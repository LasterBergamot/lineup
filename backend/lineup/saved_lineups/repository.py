"""Database access for saved lineups and their player snapshots.

Lookups return `None` when nothing matches; `user_id` filters apply only when it is not `None`
(always None until auth exists).
"""

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
    """Insert a lineup together with its player snapshots and return the reloaded row.

    The reload matters: right after the commit the in-memory snapshots are still in request
    order, so the relationship is refreshed to apply its cap-number ordering and make the create
    response match a later GET.
    """
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
    # The snapshots are still in request order in the identity map; reloading applies the
    # relationship's order_by (cap number) so POST returns the same order as GET.
    await session.refresh(lineup, ["player_snapshots"])
    return await get_saved_lineup_by_id(session, lineup.id)


async def get_saved_lineup_by_id(
    session: AsyncSession,
    lineup_id: uuid.UUID,
) -> SavedLineup | None:
    """Fetch a lineup by id regardless of owner (internal use after creating one)."""
    result = await session.execute(
        select(SavedLineup).where(SavedLineup.id == lineup_id)
    )
    return result.scalar_one_or_none()


async def get_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> SavedLineup | None:
    """Fetch one lineup, restricted to `user_id` when given. Returns `None` if not found."""
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
    """One page of lineups, optionally for one `source_team_id`, ordered by
    `(created_at, id)` so paging is stable, plus the total count before paging.
    """
    query = select(SavedLineup)
    if user_id is not None:
        query = query.where(SavedLineup.user_id == user_id)
    if source_team_id is not None:
        query = query.where(SavedLineup.source_team_id == source_team_id)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    query = (
        query.order_by(SavedLineup.created_at, SavedLineup.id)
        .limit(limit)
        .offset(offset)
    )
    items = list((await session.execute(query)).scalars().all())
    return items, total


async def delete_saved_lineup(
    session: AsyncSession,
    lineup: SavedLineup,
) -> None:
    """Delete a lineup; its player snapshots go with it (`ON DELETE CASCADE`)."""
    await session.delete(lineup)
    await session.commit()
