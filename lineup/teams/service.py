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
    return await repository.create_team(
        session, name=name, owner_id=owner_id, is_public=is_public
    )


async def get_team_or_404(
    session: AsyncSession,
    team_id: uuid.UUID,
    owner_id: uuid.UUID | None,
) -> Team:
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
    return await repository.list_teams(
        session, owner_id=owner_id, limit=limit, offset=offset
    )


async def search_teams_pool(
    session: AsyncSession,
    search: str | None,
    limit: int,
) -> list[Team]:
    return await repository.search_teams_pool(session, search=search, limit=limit)


async def update_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    name: str,
    owner_id: uuid.UUID | None,
) -> Team:
    team = await get_team_or_404(session, team_id=team_id, owner_id=owner_id)
    return await repository.update_team(session, team=team, name=name)


async def delete_team(
    session: AsyncSession,
    team_id: uuid.UUID,
    owner_id: uuid.UUID | None,
) -> TeamDeleteResponse:
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
