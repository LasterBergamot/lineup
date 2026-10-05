"""Database access for teams: the only place that writes team queries.

Functions take an `owner_id`; when it is `None` (always, until auth exists) no owner filter is
applied. Lookups return `None` when nothing matches; turning that into a 404 is the service's job.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player, Team


async def create_team(
    session: AsyncSession,
    name: str,
    owner_id: uuid.UUID | None,
    is_public: bool,
) -> Team:
    """Insert a team, commit, and return it with database-generated fields loaded."""
    team = Team(id=uuid.uuid4(), name=name, owner_id=owner_id, is_public=is_public)
    session.add(team)
    await session.commit()
    await session.refresh(team)
    return team


async def get_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    owner_id: uuid.UUID | None,
) -> Team | None:
    """Fetch one team, restricted to `owner_id` when given. Returns `None` if not found or not owned."""
    query = select(Team).where(Team.id == team_id)
    if owner_id is not None:
        query = query.where(Team.owner_id == owner_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_team_by_id(
    session: AsyncSession,
    team_id: uuid.UUID,
) -> Team | None:
    """Ownerless lookup — used to resolve a soft team reference (e.g. an
    opponent) regardless of who owns it."""
    result = await session.execute(select(Team).where(Team.id == team_id))
    return result.scalar_one_or_none()


async def list_teams(
    session: AsyncSession,
    owner_id: uuid.UUID | None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Team], int]:
    """One page of teams ordered by `(name, id)` (the id breaks ties so pages never repeat or
    skip rows), plus the total count before paging.
    """
    query = select(Team)
    if owner_id is not None:
        query = query.where(Team.owner_id == owner_id)
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    query = query.order_by(Team.name, Team.id).limit(limit).offset(offset)
    items = list((await session.execute(query)).scalars().all())
    return items, total


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    """Public teams whose name contains `search` (case-insensitive, literal match: `%` and
    `_` are escaped, not wildcards), ordered by `(name, id)`, at most `limit`.
    """
    query = select(Team).where(Team.is_public.is_(True))
    if search:
        query = query.where(Team.name.icontains(search, autoescape=True))
    query = query.order_by(Team.name, Team.id).limit(limit)
    return list((await session.execute(query)).scalars().all())


async def update_team(
    session: AsyncSession,
    team: Team,
    name: str,
) -> Team:
    """Rename a team, commit, and return the refreshed row."""
    team.name = name
    await session.commit()
    await session.refresh(team)
    return team


async def count_players_for_team(
    session: AsyncSession,
    team_id: uuid.UUID,
) -> int:
    """Returns the number of roster players currently assigned to this team."""
    result = await session.scalar(select(func.count()).where(Player.team_id == team_id))
    return result or 0


async def delete_team(
    session: AsyncSession,
    team: Team,
) -> None:
    """Delete the team and commit. The caller must have checked the roster is empty."""
    await session.delete(team)
    await session.commit()
