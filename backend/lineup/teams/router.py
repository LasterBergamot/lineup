"""HTTP endpoints under `/teams`: CRUD, the shared opponent pool and a team's recent opponents.

A team is a workspace shared by its members. Routes that take a team id answer `404` when the
caller is not a member (whether or not the team exists), and `403` when a member lacks the
`owner` role for an owner-only action.

`/teams/pool` is registered before `/teams/{team_id}` so "pool" is not parsed as a team id.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.auth.dependencies import get_current_user_id
from lineup.db.engine import get_session
from lineup.teams import service
from lineup.teams.schemas import (
    PaginatedTeams,
    TeamCreate,
    TeamDeleteResponse,
    TeamPoolItem,
    TeamResponse,
    TeamUpdate,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=PaginatedTeams)
async def list_teams(
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items to return (1-200).")
    ] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedTeams:
    """List the teams you belong to, ordered by name, each with your `role`. Paginated: `limit`
    is 1-200 (default 20) and `offset` starts at 0; the response carries `total` so clients
    can page.
    """
    items, total = await service.list_teams(
        session, user_id=user_id, limit=limit, offset=offset
    )
    return PaginatedTeams(
        items=[TeamResponse.from_team(team, role) for team, role in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    body: TeamCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> TeamResponse:
    """Create a team; you become its owner. `is_public` (default true) lists its name in the
    opponent directory, which never reveals anything else about the team."""
    team, role = await service.create_team(
        session, name=body.name, created_by=user_id, is_public=body.is_public
    )
    return TeamResponse.from_team(team, role)


# Registered before /{team_id} so "pool" isn't swallowed as a team_id path param
@router.get("/pool", response_model=list[TeamPoolItem])
async def search_teams_pool(
    search: Annotated[
        str | None,
        Query(max_length=120, description="Filter by team name (literal match)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
    _user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[TeamPoolItem]:
    """Search the opponent directory (sign-in required). Only teams that chose to be listed
    (`is_public`) are returned, and only their `id` and `name`. `search` is a literal,
    case-insensitive substring.
    """
    teams = await service.search_teams_pool(session, search=search, limit=limit)
    return [TeamPoolItem.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> TeamResponse:
    """Get one of your teams by id (404 if unknown or you are not a member)."""
    team, role = await service.get_team_or_404(
        session, team_id=team_id, user_id=user_id
    )
    return TeamResponse.from_team(team, role)


@router.get("/{team_id}/opponents/recent", response_model=list[str])
async def recent_opponents(
    team_id: uuid.UUID,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[str]:
    """Opponent names used in this team's saved lineups, most recent first (no duplicates). Lets
    the lineup form suggest opponents that are not in the directory. 404 unless you are a
    member of the team.
    """
    return await service.recent_opponents(
        session, team_id=team_id, user_id=user_id, limit=limit
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    body: TeamUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> TeamResponse:
    """Rename a team and/or list or unlist it in the opponent directory (`is_public`, left
    unchanged when omitted). Owners only: 403 for other members, 404 for non-members."""
    team, role = await service.update_team(
        session,
        team_id=team_id,
        name=body.name,
        is_public=body.is_public,
        user_id=user_id,
    )
    return TeamResponse.from_team(team, role)


@router.delete("/{team_id}", response_model=TeamDeleteResponse)
async def delete_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> TeamDeleteResponse:
    """Delete a team (owners only: 403 for other members, 404 for non-members). Returns 409 while
    players are on its roster or saved lineups live in it; lineups that merely mention the team
    as their source or opponent are unaffected because they store copies.
    """
    return await service.delete_team(session, team_id=team_id, user_id=user_id)
