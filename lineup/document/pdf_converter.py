import subprocess
import tempfile
from pathlib import Path


class PdfConverter:
    def convert(self, docx_bytes: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_path = tmpdir_path / "input.docx"
            input_path.write_bytes(docx_bytes)

            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(tmpdir_path),
                    str(input_path),
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed: {result.stderr.decode()}"
                )

            return (tmpdir_path / "input.pdf").read_bytes()
