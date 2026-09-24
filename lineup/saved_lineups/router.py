from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.auth.dependencies import get_current_user_id
from lineup.db.engine import get_session
from lineup.saved_lineups import service
from lineup.saved_lineups.schemas import (
    PaginatedSavedLineups,
    SavedLineupCreate,
    SavedLineupResponse,
)
from lineup.water_polo.water_polo_lineup_creator import WaterPoloLineupCreator
from lineup.water_polo.water_polo_lineup_dto import WaterPoloLineupDTO
from lineup.api.router import FileFormat

router = APIRouter(prefix="/lineups/saved", tags=["saved-lineups"])

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.get("", response_model=PaginatedSavedLineups)
async def list_saved_lineups(
    limit: Annotated[
        int, Query(ge=0, description="Max items to return. 0 = no limit.")
    ] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    source_team_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> PaginatedSavedLineups:
    items, total = await service.list_saved_lineups(
        session,
        user_id=user_id,
        source_team_id=source_team_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedSavedLineups(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=SavedLineupResponse, status_code=201)
async def create_saved_lineup(
    body: SavedLineupCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> SavedLineupResponse:
    return await service.create_saved_lineup(session, data=body, user_id=user_id)


@router.get("/{lineup_id}", response_model=SavedLineupResponse)
async def get_saved_lineup(
    lineup_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> SavedLineupResponse:
    return await service.get_saved_lineup_or_404(
        session, lineup_id=lineup_id, user_id=user_id
    )


@router.delete("/{lineup_id}", status_code=204)
async def delete_saved_lineup(
    lineup_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> None:
    await service.delete_saved_lineup(session, lineup_id=lineup_id, user_id=user_id)


@router.post("/{lineup_id}/generate")
async def generate_from_saved_lineup(
    lineup_id: uuid.UUID,
    file_format: Annotated[
        FileFormat,
        Query(alias="format", description="Output format: pdf or docx"),
    ] = FileFormat.PDF,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> Response:
    """Generate a document from a previously saved lineup."""
    lineup_response = await service.get_saved_lineup_or_404(
        session, lineup_id=lineup_id, user_id=user_id
    )

    players = [
        WaterPoloLineupDTO.Player.PlayerBuilder()
        .set_cap_number(p.cap_number)
        .set_name(p.name)
        .set_nssz_number(p.nssz_number)
        .build()
        for p in lineup_response.players
    ]
    dto = (
        WaterPoloLineupDTO.WaterPoloLineupDTOBuilder()
        .set_match(lineup_response.match_name)
        .set_division(lineup_response.division)
        .set_team_name(lineup_response.team_name)
        .set_cap(lineup_response.cap)
        .set_date(lineup_response.date)
        .set_coach(lineup_response.coach)
        .set_doctor(lineup_response.doctor or "")
        .set_assistant_coach(lineup_response.assistant_coach or "")
        .set_team_leader(lineup_response.team_leader or "")
        .set_ball_thrower(lineup_response.ball_thrower or "")
        .set_players(players)
        .build()
    )

    creator = WaterPoloLineupCreator()
    team_name = lineup_response.team_name
    date = lineup_response.date

    if file_format == FileFormat.PDF:
        content = creator.create_pdf_bytes(dto)
        media_type = "application/pdf"
        filename = f"rajtlista_{team_name}_{date}.pdf"
    else:
        content = creator.create_document_bytes(dto)
        media_type = DOCX_MEDIA_TYPE
        filename = f"rajtlista_{team_name}_{date}.docx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
