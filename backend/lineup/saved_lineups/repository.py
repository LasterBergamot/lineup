"""Database access for saved lineups and their player snapshots.

A saved lineup lives in a team's workspace (`team_id`) and every member of that team may use it,
so lookups are keyed by the signed-in `user_id` and restricted to teams they belong to
(`team_repo.member_team_ids`). They return `None` when nothing matches; the service turns that into a 404.
An edit (`update_saved_lineup`) is a compare-and-swap on `updated_at`, so a concurrent edit is
detected by the database itself rather than by a read-then-write check.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from datetime import time as time_type
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot, SavedLineup
from lineup.teams.repository import member_team_ids


async def create_saved_lineup(
    session: AsyncSession,
    team_name: str,
    opponent_name: str,
    match_name: str,
    division: str,
    cap: str,
    date: str,
    match_date: date_type | None,
    match_time: time_type | None,
    location: str | None,
    coach: str,
    doctor: str | None,
    assistant_coach: str | None,
    team_leader: str | None,
    ball_thrower: str | None,
    created_by: uuid.UUID,
    team_id: uuid.UUID,
    source_team_id: uuid.UUID | None,
    source_opponent_id: uuid.UUID | None,
    player_snapshots: list[LineupPlayerSnapshot],
) -> SavedLineup:
    """Insert a lineup together with its player snapshots and return the reloaded row.

    The reload matters: right after the commit the in-memory snapshots are still in request
    order, so the relationship is refreshed to apply its cap-number ordering and make the create
    response match a later GET. `created_at` and `updated_at` come from one clock reading, so a
    new lineup has them equal.
    """
    now = datetime.now(UTC)
    lineup = SavedLineup(
        id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        team_name=team_name,
        opponent_name=opponent_name,
        match_name=match_name,
        division=division,
        cap=cap,
        date=date,
        match_date=match_date,
        match_time=match_time,
        location=location,
        coach=coach,
        doctor=doctor,
        assistant_coach=assistant_coach,
        team_leader=team_leader,
        ball_thrower=ball_thrower,
        created_by=created_by,
        team_id=team_id,
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


async def update_saved_lineup(
    session: AsyncSession,
    lineup_id: uuid.UUID,
    expected_updated_at: datetime,
    fields: dict[str, Any],
    player_snapshots: list[LineupPlayerSnapshot],
) -> SavedLineup | None:
    """Replace a lineup's columns and all of its player snapshots in one transaction.

    `fields` maps column names to their new values (the service passes every editable column).
    The row is only changed while its `updated_at` still equals `expected_updated_at`, checked
    by the `UPDATE ... WHERE` itself: on Postgres a concurrent edit waits for this row lock and
    then matches nothing, so exactly one of two simultaneous edits wins. Returns `None` (and
    rolls back, changing nothing) when the row no longer matches, which the service reports as
    409; the caller has already checked that the lineup exists and is the user's. Otherwise
    returns the reloaded lineup.

    The old snapshots are deleted *before* the new ones are inserted, because the unique index
    on `(saved_lineup_id, cap_number)` would otherwise see the same cap number twice.
    """
    result = await session.execute(
        update(SavedLineup)
        .where(
            SavedLineup.id == lineup_id,
            SavedLineup.updated_at == expected_updated_at,
        )
        .values(**fields, updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        await session.rollback()
        return None
    await session.execute(
        delete(LineupPlayerSnapshot).where(
            LineupPlayerSnapshot.saved_lineup_id == lineup_id
        )
    )
    for snapshot in player_snapshots:
        snapshot.saved_lineup_id = lineup_id
    session.add_all(player_snapshots)
    await session.commit()
    # The session may still hold the lineup as loaded before the edit (expire_on_commit is
    # off), so read it again from the database instead of the identity map.
    result = await session.execute(
        select(SavedLineup)
        .where(SavedLineup.id == lineup_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


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
    user_id: uuid.UUID,
) -> SavedLineup | None:
    """Fetch one lineup from the workspace of a team `user_id` belongs to. Returns `None` if it
    doesn't exist or lives in a team the user is not in."""
    result = await session.execute(
        select(SavedLineup).where(
            SavedLineup.id == lineup_id,
            SavedLineup.team_id.in_(member_team_ids(user_id)),
        )
    )
    return result.scalar_one_or_none()


async def list_saved_lineups(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_team_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    opponent: str | None = None,
    location: str | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[SavedLineup], int]:
    """One page of the lineups of all teams `user_id` belongs to, newest match first, plus the
    total count before paging.

    The membership filter is always applied; every other filter is optional and they are
    AND-ed together. `team_id` and `source_team_id` match exactly. `opponent` and `location` are
    case-insensitive *contains* matches on the snapshot's `opponent_name` and `location`, and
    `%` and `_` in them are escaped (`autoescape=True`) so they are literal characters, not
    wildcards; the term only ever travels as a bound parameter. `date_from` and `date_to` are
    inclusive bounds on `match_date`; a lineup without a structured date (legacy free text)
    never matches a date bound. A caller passes `None` or a non-blank string, the router drops
    blank terms.

    Order: `match_date` descending with undated lineups last, then `created_at` and `id`
    descending, so paging is stable and a team's latest match comes first.
    """
    query = select(SavedLineup).where(SavedLineup.team_id.in_(member_team_ids(user_id)))
    if team_id is not None:
        query = query.where(SavedLineup.team_id == team_id)
    if source_team_id is not None:
        query = query.where(SavedLineup.source_team_id == source_team_id)
    if opponent is not None:
        query = query.where(
            SavedLineup.opponent_name.icontains(opponent, autoescape=True)
        )
    if location is not None:
        query = query.where(SavedLineup.location.icontains(location, autoescape=True))
    if date_from is not None:
        query = query.where(SavedLineup.match_date >= date_from)
    if date_to is not None:
        query = query.where(SavedLineup.match_date <= date_to)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    query = (
        query.order_by(
            SavedLineup.match_date.desc().nulls_last(),
            SavedLineup.created_at.desc(),
            SavedLineup.id.desc(),
        )
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
