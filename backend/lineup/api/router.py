"""`POST /lineups`: build a lineup document straight from the request, without touching the database."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from lineup.api.file_response import FileFormat, build_file_response
from lineup.api.models import LineupRequest
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

router = APIRouter(prefix="/lineups", tags=["lineups"])


@router.post("", status_code=200)
async def create_lineup(
    request: LineupRequest,
    file_format: Annotated[
        FileFormat,
        Query(alias="format", description="Output format of the generated file"),
    ] = FileFormat.PDF,
) -> Response:
    """Generate a lineup sheet from the request body and return it as a file download.

    `format=pdf` (default) converts through LibreOffice, which only exists in the container;
    `format=docx` returns the filled template directly. Nothing is stored.
    """
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
    return await build_file_response(dto, file_format)
