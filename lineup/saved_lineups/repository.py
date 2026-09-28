from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot, SavedLineup


async def create_saved_lineup(
    session: AsyncSession,
    team_name: str,
    opponent_name: str,
    match_name: str,
    division: str,
    cap: str,
    date: str,
    coach: str,
    doctor: str | None,
    assistant_coach: str | None,
    team_leader: str | None,
    ball_thrower: str | None,
    user_id: uuid.UUID | None,
    source_team_id: uuid.UUID | None,
    source_opponent_id: uuid.UUID | None,
    player_snapshots: list[LineupPlayerSnapshot],
) -> SavedLineup:
    lineup = SavedLineup(
        id=uuid.uuid4(),
        team_name=team_name,
        opponent_name=opponent_name,
        match_name=match_name,
        division=division,
        cap=cap,
        date=date,
        coach=coach,
        doctor=doctor,
        assistant_coach=assistant_coach,
        team_leader=team_leader,
        ball_thrower=ball_thrower,
        user_id=user_id,
        source_team_id=source_team_id,
        source_opponent_id=source_opponent_id,
        player_snapshots=player_snapshots,
    )
    session.add(lineup)
    await session.commit()
    return await get_saved_lineup_by_id(session, lineup.id)


async def get_saved_lineup_by_id(
    session: AsyncSession,
    lineup_id: uuid.UUID,
) -> SavedLineup | None:
    result = await session.execute(
        select(SavedLineup).where(SavedLineup.id == lineup_id)
    )
    return result.scalar_one_or_none()


async def get_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> SavedLineup | None:
    query = select(SavedLineup).where(SavedLineup.id == lineup_id)
    if user_id is not None:
        query = query.where(SavedLineup.user_id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_saved_lineups(
    session: AsyncSession,
    user_id: uuid.UUID | None,
    source_team_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[SavedLineup], int]:
    query = select(SavedLineup)
    if user_id is not None:
        query = query.where(SavedLineup.user_id == user_id)
    if source_team_id is not None:
        query = query.where(SavedLineup.source_team_id == source_team_id)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    if limit > 0:
        query = query.limit(limit)
    query = query.offset(offset)
    items = list((await session.execute(query)).scalars().all())
    return items, total


async def delete_saved_lineup(
    session: AsyncSession,
    lineup: SavedLineup,
) -> None:
    await session.delete(lineup)
    await session.commit()
