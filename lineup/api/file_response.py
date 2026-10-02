import logging
import re
import subprocess
import unicodedata
from enum import Enum
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

logger = logging.getLogger(__name__)

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class FileFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


def content_disposition(filename: str) -> str:
    """Build an attachment header that survives any user-supplied filename.

    Header values are latin-1 encoded, so Hungarian ő/ű (and any quote or
    semicolon) can't go into a plain ``filename="..."``. The RFC 6266
    ``filename*`` parameter carries the real UTF-8 name; ``filename`` is an
    accent-stripped ASCII fallback for clients that don't read ``filename*``.
    """
    ascii_name = (
        unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    )
    fallback = re.sub(r'[\x00-\x1f\x7f"\\/;]', "_", ascii_name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def _render(dto: WaterPoloLineupDTO, file_format: FileFormat) -> bytes:
    creator = WaterPoloLineupCreator()
    if file_format == FileFormat.PDF:
        return creator.create_pdf_bytes(dto)
    return creator.create_document_bytes(dto)


async def build_file_response(
    dto: WaterPoloLineupDTO, file_format: FileFormat
) -> Response:
    """Render the lineup and wrap it in a download response.

    Rendering runs in the threadpool: PDF conversion is a blocking LibreOffice
    subprocess that can take seconds, and must not stall the event loop.
    """
    try:
        content = await run_in_threadpool(_render, dto, file_format)
    except subprocess.TimeoutExpired:
        logger.error("PDF conversion timed out")
        raise HTTPException(status_code=504, detail="PDF conversion timed out")
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Document generation failed")

    if file_format == FileFormat.PDF:
        media_type = PDF_MEDIA_TYPE
    else:
        media_type = DOCX_MEDIA_TYPE
    filename = f"rajtlista_{dto.team_name}_{dto.date}.{file_format.value}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )
