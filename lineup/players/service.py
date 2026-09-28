from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player
from lineup.players import repository


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
) -> Player:
    return await repository.create_player(
        session, name=name, nssz_number=nssz_number, user_id=user_id, team_id=team_id
    )


async def get_player_or_404(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> Player:
    player = await repository.get_player(session, player_id=player_id, user_id=user_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


async def list_players(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Player], int]:
    return await repository.list_players(
        session, user_id=user_id, team_id=team_id, limit=limit, offset=offset
    )


async def update_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    name: str,
    nssz_number: str,
    team_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> Player:
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    return await repository.update_player(
        session, player=player, name=name, nssz_number=nssz_number, team_id=team_id
    )


async def delete_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> None:
    player = await get_player_or_404(session, player_id=player_id, user_id=user_id)
    await repository.delete_player(session, player=player)
