import subprocess
import tempfile
from pathlib import Path

# LibreOffice can be slow on its first invocation in a fresh container (it has to build a
# user profile), so allow generous headroom before giving up.
CONVERSION_TIMEOUT_SECONDS = 120


class PdfConverter:
    def convert(self, docx_bytes: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_path = tmpdir_path / "input.docx"
            input_path.write_bytes(docx_bytes)

            # A private, per-call user profile avoids the "another instance is already
            # running" clash when conversions overlap, and guarantees a writable profile
            # dir even when $HOME is not set.
            profile_uri = (tmpdir_path / "profile").as_uri()

            result = subprocess.run(
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
                capture_output=True,
                timeout=CONVERSION_TIMEOUT_SECONDS,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed: {result.stderr.decode()}"
                )

            return (tmpdir_path / "input.pdf").read_bytes()
