"""Business rules for teams, between the router (HTTP) and the repository (SQL).

Raises `HTTPException` directly (there are no custom exception types in this project).
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Team
from lineup.teams import repository
from lineup.teams.schemas import TeamDeleteResponse


async def create_team(
    session: AsyncSession,
    name: str,
    owner_id: uuid.UUID | None,
    is_public: bool,
) -> Team:
    """Create a team owned by `owner_id` (None until auth exists)."""
    return await repository.create_team(
        session, name=name, owner_id=owner_id, is_public=is_public
    )


async def get_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    owner_id: uuid.UUID | None,
) -> Team:
    """Return the team or raise 404 "Team not found" (also when it exists but is not owned)."""
    team = await repository.get_team(session, team_id=team_id, owner_id=owner_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


async def list_teams(
    session: AsyncSession,
    owner_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Team], int]:
    """One page of the caller's teams and the total count."""
    return await repository.list_teams(
        session, owner_id=owner_id, limit=limit, offset=offset
    )


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    """Search the shared opponent pool (public teams only); no ownership check by design."""
    return await repository.search_teams_pool(session, search=search, limit=limit)


async def update_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    name: str,
    owner_id: uuid.UUID | None,
) -> Team:
    """Rename a team; 404 if it is not found."""
    team = await get_team_or_404(session, team_id=team_id, owner_id=owner_id)
    return await repository.update_team(session, team=team, name=name)


async def delete_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    owner_id: uuid.UUID | None,
) -> TeamDeleteResponse:
    """Delete a team. Raises 404 if not found and 409 if players are still on its roster.

    The 409 is an application-level check; the database's `RESTRICT` is only a backstop.

    """
    team = await get_team_or_404(session, team_id=team_id, owner_id=owner_id)
    player_count = await repository.count_players_for_team(session, team_id=team.id)
    if player_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete team: it still has {player_count} player(s) on its "
                "roster. Remove or reassign the players before deleting the team."
            ),
        )
    await repository.delete_team(session, team=team)
    return TeamDeleteResponse(id=team.id, name=team.name, deleted=True)
