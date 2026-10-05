"""Database access for teams: the only place that writes team queries.

A team is a workspace: a user may use it when they have a row in `team_members`. Every lookup
here is therefore keyed by the signed-in `user_id` and joins through `team_members`; a team the
caller does not belong to simply does not exist for them (`None`), and turning that into a 404 is
the service's job. `member_team_ids()` is the one building block other modules use to apply
the same rule to their own tables.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player, SavedLineup, Team, TeamMember, TeamRole

TeamWithRole = tuple[Team, str]


def member_team_ids(user_id: uuid.UUID) -> Select:
    """A subquery of the ids of every team `user_id` belongs to.

    Use it as `Table.team_id.in_(member_team_ids(user_id))`: that is the access rule for
    players and saved lineups.
    """
    return select(TeamMember.team_id).where(TeamMember.user_id == user_id)


async def create_team(
    session: AsyncSession,
    name: str,
    created_by: uuid.UUID,
    is_public: bool,
) -> Team:
    """Insert a team and its creator's `owner` membership in one transaction, commit, and return
    the team with database-generated fields loaded."""
    team = Team(id=uuid.uuid4(), name=name, created_by=created_by, is_public=is_public)
    session.add(team)
    session.add(
        TeamMember(team_id=team.id, user_id=created_by, role=TeamRole.OWNER.value)
    )
    await session.commit()
    await session.refresh(team)
    return team


async def get_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamWithRole | None:
    """Fetch one team together with the caller's role in it.

    Returns `None` if the team doesn't exist or `user_id` is not a member of it (the two are
    deliberately indistinguishable).
    """
    result = await session.execute(
        select(Team, TeamMember.role)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(Team.id == team_id, TeamMember.user_id == user_id)
    )
    row = result.one_or_none()
    return None if row is None else (row[0], row[1])


async def get_team_visible(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Team | None:
    """Fetch a team the caller may use as an *opponent*: one they belong to, or one listed in
    the opponent directory (`is_public`). Returns `None` otherwise."""
    result = await session.execute(
        select(Team).where(
            Team.id == team_id,
            Team.id.in_(member_team_ids(user_id)) | Team.is_public.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_teams(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TeamWithRole], int]:
    """One page of the teams `user_id` belongs to, each with their role, ordered by
    `(name, id)` (the id breaks ties so pages never repeat or skip rows), plus the total count
    before paging.
    """
    query = (
        select(Team, TeamMember.role)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(TeamMember.user_id == user_id)
    )
    total: int = (
        await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    )
    query = query.order_by(Team.name, Team.id).limit(limit).offset(offset)
    rows = (await session.execute(query)).all()
    return [(row[0], row[1]) for row in rows], total


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    """Teams listed in the opponent directory (`is_public`) whose name contains `search`
    (case-insensitive, literal match: `%` and `_` are escaped, not wildcards), ordered by
    `(name, id)`, at most `limit`.
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
    is_public: bool | None,
) -> Team:
    """Rename a team and, when `is_public` is given, list or unlist it. Commits and returns the
    refreshed row."""
    team.name = name
    if is_public is not None:
        team.is_public = is_public
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


async def count_saved_lineups_for_team(
    session: AsyncSession,
    team_id: uuid.UUID,
) -> int:
    """Returns the number of saved lineups that live in this team's workspace."""
    result = await session.scalar(
        select(func.count()).where(SavedLineup.team_id == team_id)
    )
    return result or 0


async def recent_opponents(
    session: AsyncSession,
    team_id: uuid.UUID,
    limit: int,
) -> list[str]:
    """Distinct opponent names from the team's saved lineups, most recently used first (ties by
    name), at most `limit`. Covers opponents that are not in the directory."""
    latest = func.max(SavedLineup.created_at)
    query = (
        select(SavedLineup.opponent_name)
        .where(SavedLineup.team_id == team_id)
        .group_by(SavedLineup.opponent_name)
        .order_by(latest.desc(), SavedLineup.opponent_name)
        .limit(limit)
    )
    return list((await session.execute(query)).scalars().all())


async def delete_team(
    session: AsyncSession,
    team: Team,
) -> None:
    """Delete the team and commit; its memberships and invitations go with it. The caller must
    have checked that no players or saved lineups remain."""
    await session.delete(team)
    await session.commit()
