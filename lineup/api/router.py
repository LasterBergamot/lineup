from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException

from lineup.api.models import LineupRequest, LineupResponse
from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO

router = APIRouter(prefix="/lineups", tags=["lineups"])
logger = logging.getLogger(__name__)


@router.post("", response_model=LineupResponse, status_code=200)
def create_lineup(request: LineupRequest) -> LineupResponse:
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
        doc_bytes = WaterPoloLineupCreator().create_document_bytes(dto)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Document template not found")
    except Exception as e:
        logger.error("Document generation failed: %s", e)
        raise HTTPException(status_code=500, detail="Document generation failed")

    return LineupResponse(
        document=base64.b64encode(doc_bytes).decode("utf-8"),
        filename=f"rajtlista_{request.team_name}_{request.date}.docx",
    )
