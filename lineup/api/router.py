import logging
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from lineup.api.models import LineupRequest
from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

router = APIRouter(prefix="/lineups", tags=["lineups"])
logger = logging.getLogger(__name__)

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class FileFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


@router.post("", status_code=200)
def create_lineup(
    request: LineupRequest,
    file_format: Annotated[
        FileFormat,
        Query(alias="format", description="Output format of the generated file"),
    ] = FileFormat.PDF,
) -> Response:
    players = [
        WaterPoloLineupDTO.Player.PlayerBuilder()
        .set_cap_number(p.cap_number)
        .set_name(p.name)
        .set_nssz_number(p.nssz_number)
        .build()
        for p in request.players
    ]
    dto = (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match(request.match)
        .set_division(request.division)
        .set_team_name(request.team_name)
        .set_cap(request.cap)
        .set_date(request.date)
        .set_coach(request.coach)
        .set_doctor(request.doctor)
        .set_assistant_coach(request.assistant_coach)
        .set_team_leader(request.team_leader)
        .set_ball_thrower(request.ball_thrower)
        .set_players(players)
        .build()
    )
    try:
        creator = WaterPoloLineupCreator()
        if file_format == FileFormat.PDF:
            content = creator.create_pdf_bytes(dto)
            media_type = "application/pdf"
            filename = f"rajtlista_{request.team_name}_{request.date}.pdf"
        else:
            content = creator.create_document_bytes(dto)
            media_type = DOCX_MEDIA_TYPE
            filename = f"rajtlista_{request.team_name}_{request.date}.docx"
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Document template not found")
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Document generation failed")

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
