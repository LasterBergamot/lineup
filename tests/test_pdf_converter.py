import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lineup.document.pdf_converter import PdfConverter, CONVERSION_TIMEOUT_SECONDS


def test_convert_success():
    fake_pdf = b"%PDF-1.4 test"
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        outdir = cmd[cmd.index("--outdir") + 1]
        (Path(outdir) / "input.pdf").write_bytes(fake_pdf)
        result = MagicMock()
        result.returncode = 0
        return result

    with patch("subprocess.run", side_effect=fake_run):
        result = PdfConverter().convert(b"fake docx bytes")

    assert result == fake_pdf
    # a private per-call profile and a generous timeout are always passed
    assert any(arg.startswith("-env:UserInstallation=") for arg in captured["cmd"])
    assert captured["kwargs"]["timeout"] == CONVERSION_TIMEOUT_SECONDS


def test_convert_raises_on_libreoffice_failure():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b"LibreOffice error"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="LibreOffice conversion failed"):
            PdfConverter().convert(b"fake docx bytes")
