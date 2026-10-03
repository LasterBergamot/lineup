from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player


async def create_player(
    session: AsyncSession,
    name: str,
    nssz_number: str,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None,
) -> Player:
    player = Player(
        id=uuid.uuid4(),
        name=name,
        nssz_number=nssz_number,
        user_id=user_id,
        team_id=team_id,
    )
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player


async def get_player(
    session: AsyncSession,
    player_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> Player | None:
    query = select(Player).where(Player.id == player_id)
    if user_id is not None:
        query = query.where(Player.user_id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_players(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    team_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Player], int]:
    query = select(Player)
    if user_id is not None:
        query = query.where(Player.user_id == user_id)
    if team_id is not None:
        query = query.where(Player.team_id == team_id)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    if limit > 0:
        query = query.limit(limit)
    query = query.offset(offset)
    items = list((await session.execute(query)).scalars().all())
    return items, total


async def update_player(
    session: AsyncSession,
    player: Player,
    name: str,
    nssz_number: str,
    team_id: uuid.UUID | None,
) -> Player:
    player.name = name
    player.nssz_number = nssz_number
    player.team_id = team_id
    await session.commit()
    await session.refresh(player)
    return player


async def delete_player(
    session: AsyncSession,
    player: Player,
) -> None:
    await session.delete(player)
    await session.commit()
