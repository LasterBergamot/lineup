import logging
import os
import shutil
import signal
import subprocess
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# LibreOffice can be slow on its first invocation in a fresh container (it has to build a
# user profile), so allow generous headroom before giving up.
CONVERSION_TIMEOUT_SECONDS = 120

# How long a request may wait for a free conversion slot before the API answers 503.
QUEUE_TIMEOUT_SECONDS = 10


# Each conversion is a separate LibreOffice process with its own profile (a few hundred MB),
# so an unbounded number of parallel requests would exhaust a small machine's memory.
def read_max_concurrent(raw: str | None) -> int:
    """`PDF_MAX_CONCURRENT`, default 2. Refuses < 1 at startup: 0 would reject every PDF."""
    value = int(raw) if raw else 2
    if value < 1:
        raise ValueError("PDF_MAX_CONCURRENT must be at least 1")
    return value


MAX_CONCURRENT_CONVERSIONS = read_max_concurrent(os.getenv("PDF_MAX_CONCURRENT"))

_slots = threading.BoundedSemaphore(MAX_CONCURRENT_CONVERSIONS)

# Enough of LibreOffice's stderr to diagnose a failure without flooding the log.
_STDERR_LOG_LIMIT = 500


class ConverterBusyError(RuntimeError):
    """All conversion slots stayed busy for QUEUE_TIMEOUT_SECONDS (mapped to HTTP 503)."""


class PdfConverter:
    def convert(self, docx_bytes: bytes) -> bytes:
        if shutil.which("libreoffice") is None:
            raise RuntimeError(
                "LibreOffice is not installed (no 'libreoffice' on PATH)"
            )

        if not _slots.acquire(timeout=QUEUE_TIMEOUT_SECONDS):
            raise ConverterBusyError("All PDF conversion slots are busy")
        try:
            return self._convert(docx_bytes)
        finally:
            _slots.release()

    def _convert(self, docx_bytes: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_path = tmpdir_path / "input.docx"
            input_path.write_bytes(docx_bytes)

            # A private, per-call user profile avoids the "another instance is already
            # running" clash when conversions overlap, and guarantees a writable profile
            # dir even when $HOME is not set.
            profile_uri = (tmpdir_path / "profile").as_uri()

            # S603/S607 (subprocess call, partial executable path) ignored file-wide in
            # pyproject.toml — fixed executable + argv list, no shell, no user input.
            # start_new_session puts LibreOffice and everything it spawns (the launcher
            # script execs soffice.bin, which can fork more) into one process group.
            process = subprocess.Popen(
                [
                    "libreoffice",
                    f"-env:UserInstallation={profile_uri}",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmpdir_path),
                    str(input_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                _, stderr = process.communicate(timeout=CONVERSION_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                # subprocess.run would only kill the launcher, leaving soffice.bin running
                # (and holding its memory) after the request already got a 504.
                self._kill_group(process)
                raise

            if process.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed (exit {process.returncode}): "
                    f"{stderr.decode(errors='replace')[:_STDERR_LOG_LIMIT]}"
                )

            pdf_path = tmpdir_path / "input.pdf"
            if not pdf_path.exists():
                raise RuntimeError("LibreOffice exited successfully but wrote no PDF")
            return pdf_path.read_bytes()

    @staticmethod
    def _kill_group(process: subprocess.Popen) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            logger.debug("LibreOffice process group was already gone")
        process.communicate()
