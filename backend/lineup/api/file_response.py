"""Shared download response for both generate endpoints (`POST /lineups` and `POST /lineups/saved/{id}/generate`).

Owns the rendering call, the mapping of failures to HTTP status codes (busy -> 503,
timeout -> 504, anything else -> 500) and the `Content-Disposition` header.
"""

import logging
import re
import subprocess
import unicodedata
from enum import Enum
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from lineup.document.pdf_converter import ConverterBusyError
from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

logger = logging.getLogger(__name__)

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


# Sent as Retry-After when every conversion slot is busy.
QUEUE_RETRY_AFTER_SECONDS = 5


class FileFormat(str, Enum):
    """Output format of a generated lineup, taken from the `format` query parameter."""

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


def download_filename(team_name: str, date: str, extension: str) -> str:
    """Build ``rajtlista_<team>_<date>.<extension>`` as a tidy, single-dotted file name.

    The date is free text as printed on the sheet (``2024. 12. 21.``), so used as-is it left
    spaces and a ``..`` before the extension. Whitespace in the team name becomes ``_`` and the
    date's dots and spaces collapse into ``-`` (``2024-12-21``). Only the name is changed: the
    printed document keeps the date exactly as typed.
    """
    team = re.sub(r"\s+", "_", team_name.strip()).rstrip(".")
    day = re.sub(r"[\s.]+", "-", date).strip("-")
    return f"rajtlista_{team}_{day}.{extension}"


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
    except ConverterBusyError:
        logger.warning("PDF conversion rejected: all slots busy")
        raise HTTPException(
            status_code=503,
            detail="PDF conversion is busy, try again shortly",
            headers={"Retry-After": str(QUEUE_RETRY_AFTER_SECONDS)},
        )
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
    filename = download_filename(dto.team_name, dto.date, file_format.value)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": content_disposition(filename)},
    )
