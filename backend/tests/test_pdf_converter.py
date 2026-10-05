import contextlib
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import lineup.document.pdf_converter as converter_module
from lineup.document.pdf_converter import (
    CONVERSION_TIMEOUT_SECONDS,
    ConverterBusyError,
    PdfConverter,
)

FAKE_PDF = b"%PDF-1.4 test"


@pytest.fixture(autouse=True)
def libreoffice_on_path():
    """The unit tests never run LibreOffice; just pretend it is installed."""
    with patch("shutil.which", return_value="/usr/bin/libreoffice"):
        yield


def _fake_popen(returncode=0, stderr=b"", write_pdf=True, communicate=None):
    """A Popen stand-in that writes input.pdf next to the input like LibreOffice does."""

    def factory(cmd, **kwargs):
        factory.cmd, factory.kwargs = cmd, kwargs
        outdir = Path(cmd[cmd.index("--outdir") + 1])
        process = MagicMock()
        process.pid = 4242
        process.returncode = returncode

        def default_communicate(timeout=None):
            if write_pdf:
                (outdir / "input.pdf").write_bytes(FAKE_PDF)
            return b"", stderr

        process.communicate.side_effect = communicate or default_communicate
        factory.process = process
        return process

    return factory


def test_convert_success():
    factory = _fake_popen()
    with patch("subprocess.Popen", side_effect=factory):
        result = PdfConverter().convert(b"fake docx bytes")

    assert result == FAKE_PDF
    # a private per-call profile, its own process group and a generous timeout
    assert any(arg.startswith("-env:UserInstallation=") for arg in factory.cmd)
    assert factory.kwargs["start_new_session"] is True
    factory.process.communicate.assert_called_once_with(
        timeout=CONVERSION_TIMEOUT_SECONDS
    )


def test_convert_raises_on_libreoffice_failure_and_truncates_stderr():
    factory = _fake_popen(returncode=1, stderr=b"boom " * 1000, write_pdf=False)
    with patch("subprocess.Popen", side_effect=factory):
        with pytest.raises(RuntimeError, match="LibreOffice conversion failed") as exc:
            PdfConverter().convert(b"x")
    assert "exit 1" in str(exc.value)
    assert len(str(exc.value)) < 700


def test_convert_tolerates_undecodable_stderr():
    factory = _fake_popen(returncode=1, stderr=b"\xff\xfe bad", write_pdf=False)
    with patch("subprocess.Popen", side_effect=factory):
        with pytest.raises(RuntimeError, match="conversion failed"):
            PdfConverter().convert(b"x")


def test_convert_raises_a_distinct_error_when_no_pdf_was_written():
    factory = _fake_popen(returncode=0, write_pdf=False)
    with patch("subprocess.Popen", side_effect=factory):
        with pytest.raises(RuntimeError, match="wrote no PDF"):
            PdfConverter().convert(b"x")


def test_convert_raises_a_distinct_error_when_libreoffice_is_missing():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not installed"):
            PdfConverter().convert(b"x")


class TestTimeout:
    def test_timeout_kills_the_whole_process_group_and_reraises(self):
        calls = []

        def communicate(timeout=None):
            calls.append(timeout)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("libreoffice", timeout)
            return b"", b""

        factory = _fake_popen(communicate=communicate)
        with patch("subprocess.Popen", side_effect=factory):
            with patch("os.killpg") as killpg:
                with pytest.raises(subprocess.TimeoutExpired):
                    PdfConverter().convert(b"x")

        killpg.assert_called_once_with(4242, converter_module.signal.SIGKILL)
        assert len(calls) == 2, "the killed process must be reaped"

    def test_a_group_that_is_already_gone_is_not_an_error(self):
        calls = []

        def communicate(timeout=None):
            calls.append(timeout)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired("libreoffice", timeout)
            return b"", b""

        with patch(
            "subprocess.Popen", side_effect=_fake_popen(communicate=communicate)
        ):
            with patch("os.killpg", side_effect=ProcessLookupError):
                with pytest.raises(subprocess.TimeoutExpired):
                    PdfConverter().convert(b"x")

    @pytest.mark.skipif(sys.platform != "linux", reason="reads /proc")
    def test_children_of_libreoffice_do_not_survive_a_timeout(
        self, tmp_path, monkeypatch
    ):
        """A fake `libreoffice` that forks a long-running child, as soffice.bin does."""
        child_pid_file = tmp_path / "child.pid"
        script = tmp_path / "libreoffice"
        script.write_text(f"#!/bin/sh\nsleep 300 &\necho $! > {child_pid_file}\nwait\n")
        script.chmod(0o755)
        monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
        monkeypatch.setattr(converter_module, "CONVERSION_TIMEOUT_SECONDS", 1)

        with patch("shutil.which", return_value=str(script)):
            with pytest.raises(subprocess.TimeoutExpired):
                PdfConverter().convert(b"x")

        child_pid = int(child_pid_file.read_text())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _is_running(child_pid):
            time.sleep(0.05)
        assert not _is_running(child_pid), "the forked child outlived the timeout"


def _is_running(pid: int) -> bool:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] not in {"Z", "X"}


class TestConcurrencyLimit:
    def test_slots_are_capped_and_requests_queue(self, monkeypatch):
        monkeypatch.setattr(converter_module, "_slots", threading.BoundedSemaphore(2))
        running = 0
        peak = 0
        lock = threading.Lock()

        def communicate(timeout=None):
            nonlocal running, peak
            with lock:
                running += 1
                peak = max(peak, running)
            time.sleep(0.05)
            with lock:
                running -= 1
            raise subprocess.CalledProcessError(1, "x")

        results = []

        # patch() is process-wide, so enter it once instead of once per thread
        with patch(
            "subprocess.Popen", side_effect=_fake_popen(communicate=communicate)
        ):
            threads = [
                threading.Thread(
                    target=lambda: _call_and_record(results, PdfConverter().convert)
                )
                for _ in range(6)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        assert results == ["done"] * 6
        assert peak == 2

    def test_a_full_queue_raises_busy_after_the_wait(self, monkeypatch):
        slots = threading.BoundedSemaphore(1)
        slots.acquire()
        monkeypatch.setattr(converter_module, "_slots", slots)
        monkeypatch.setattr(converter_module, "QUEUE_TIMEOUT_SECONDS", 0.01)

        with patch("subprocess.Popen") as popen:
            with pytest.raises(ConverterBusyError):
                PdfConverter().convert(b"x")
        popen.assert_not_called()

    def test_busy_error_is_a_runtime_error_so_old_handlers_still_catch_it(self):
        assert issubclass(ConverterBusyError, RuntimeError)

    @pytest.mark.parametrize("outcome", ["success", "failure", "timeout"])
    def test_the_slot_is_released_whatever_happens(self, monkeypatch, outcome):
        slots = threading.BoundedSemaphore(1)
        monkeypatch.setattr(converter_module, "_slots", slots)

        def communicate(timeout=None):
            if outcome == "timeout" and timeout:
                raise subprocess.TimeoutExpired("libreoffice", timeout)
            return b"", b""

        factory = _fake_popen(
            returncode=1 if outcome == "failure" else 0,
            write_pdf=outcome == "success",
            communicate=None if outcome != "timeout" else communicate,
        )
        with patch("subprocess.Popen", side_effect=factory), patch("os.killpg"):
            with contextlib.suppress(Exception):  # only the slot accounting matters
                PdfConverter().convert(b"x")

        assert slots.acquire(blocking=False), "the slot leaked"


def _call_and_record(results, convert):
    try:
        convert(b"x")
    except subprocess.CalledProcessError:
        results.append("done")


class TestConfiguration:
    @pytest.mark.parametrize(
        ("raw", "expected"), [(None, 2), ("", 2), ("1", 1), ("8", 8)]
    )
    def test_pdf_max_concurrent_parsing(self, raw, expected):
        assert converter_module.read_max_concurrent(raw) == expected

    @pytest.mark.parametrize("raw", ["0", "-3"])
    def test_fewer_than_one_slot_is_refused(self, raw):
        with pytest.raises(ValueError, match="at least 1"):
            converter_module.read_max_concurrent(raw)
