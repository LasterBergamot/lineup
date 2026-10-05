"""HTTP endpoints under `/players`: CRUD for roster players."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.auth.dependencies import get_current_user_id
from lineup.db.engine import get_session
from lineup.players import service
from lineup.players.schemas import (
    PaginatedPlayers,
    PlayerCreate,
    PlayerResponse,
    PlayerUpdate,
)

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=PaginatedPlayers)
async def list_players(
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items to return (1-200).")
    ] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    team_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedPlayers:
    """List players ordered by creation time, optionally only one team's (`team_id`). Paginated:
    `limit` is 1-200 (default 20), `offset` starts at 0.
    """
    items, total = await service.list_players(
        session, user_id=user_id, team_id=team_id, limit=limit, offset=offset
    )
    return PaginatedPlayers(
        items=[PlayerResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PlayerResponse, status_code=201)
async def create_player(
    body: PlayerCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PlayerResponse:
    """Create a player, optionally on a team's roster. An unknown `team_id` returns 404."""
    player = await service.create_player(
        session,
        name=body.name,
        nssz_number=body.nssz_number,
        user_id=user_id,
        team_id=body.team_id,
    )
    return PlayerResponse.model_validate(player)


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(
    player_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PlayerResponse:
    """Get one player by id (404 if unknown)."""
    player = await service.get_player_or_404(
        session, player_id=player_id, user_id=user_id
    )
    return PlayerResponse.model_validate(player)


@router.put("/{player_id}", response_model=PlayerResponse)
async def update_player(
    player_id: uuid.UUID,
    body: PlayerUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PlayerResponse:
    """Replace a player's name, NSSZ number and team. An unknown player or `team_id` returns 404."""
    player = await service.update_player(
        session,
        player_id=player_id,
        name=body.name,
        nssz_number=body.nssz_number,
        team_id=body.team_id,
        user_id=user_id,
    )
    return PlayerResponse.model_validate(player)


@router.delete("/{player_id}", status_code=204)
async def delete_player(
    player_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a player. Always succeeds (204): saved lineups keep their own copy of the data."""
    await service.delete_player(session, player_id=player_id, user_id=user_id)
