"""Business rules for teams, between the router (HTTP) and the repository (SQL).

Raises `HTTPException` directly (there are no custom exception types in this project).

Two different failures, on purpose: a team the caller does not belong to is a `404` (the API never
confirms that someone else's team exists), while a *member* who lacks the `owner` role gets `403`
because they already know the team is there.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Team, TeamRole
from lineup.teams import repository
from lineup.teams.repository import TeamWithRole
from lineup.teams.schemas import TeamDeleteResponse


async def create_team(
    session: AsyncSession,
    name: str,
    created_by: uuid.UUID,
    is_public: bool,
) -> TeamWithRole:
    """Create a team; its creator becomes its `owner`."""
    team = await repository.create_team(
        session, name=name, created_by=created_by, is_public=is_public
    )
    return team, TeamRole.OWNER.value


async def get_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamWithRole:
    """Return the team and the caller's role, or raise 404 "Team not found" (also when the team
    exists but the caller is not a member)."""
    found = await repository.get_team(session, team_id=team_id, user_id=user_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return found


async def get_owned_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Team:
    """Like `get_team_or_404`, but the caller must also be an owner of the team (403 if not)."""
    team, role = await get_team_or_404(session, team_id=team_id, user_id=user_id)
    if role != TeamRole.OWNER.value:
        raise HTTPException(status_code=403, detail="Only a team owner can do this")
    return team


async def list_teams(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[TeamWithRole], int]:
    """One page of the caller's teams (with their role) and the total count."""
    return await repository.list_teams(
        session, user_id=user_id, limit=limit, offset=offset
    )


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    """Search the opponent directory (listed teams only); no membership check by design."""
    return await repository.search_teams_pool(session, search=search, limit=limit)


async def recent_opponents(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int,
) -> list[str]:
    """Opponent names the team used before, newest first. 404 unless the caller is a member."""
    await get_team_or_404(session, team_id=team_id, user_id=user_id)
    return await repository.recent_opponents(session, team_id=team_id, limit=limit)


async def update_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    name: str,
    is_public: bool | None,
    user_id: uuid.UUID,
) -> TeamWithRole:
    """Rename a team and/or list/unlist it in the opponent directory. Owner only."""
    team = await get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    team = await repository.update_team(
        session, team=team, name=name, is_public=is_public
    )
    return team, TeamRole.OWNER.value


async def delete_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TeamDeleteResponse:
    """Delete a team (owner only). Raises 404/403 as above and 409 while players or saved
    lineups are still in its workspace.

    The 409 is an application-level check; the database's `RESTRICT` is only a backstop.

    """
    team = await get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    player_count = await repository.count_players_for_team(session, team_id=team.id)
    if player_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete team: it still has {player_count} player(s) on its "
                "roster. Remove or reassign the players before deleting the team."
            ),
        )
    lineup_count = await repository.count_saved_lineups_for_team(
        session, team_id=team.id
    )
    if lineup_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete team: it still has {lineup_count} saved lineup(s). "
                "Delete them before deleting the team."
            ),
        )
    await repository.delete_team(session, team=team)
    return TeamDeleteResponse(id=team.id, name=team.name, deleted=True)
