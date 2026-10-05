"""HTTP endpoints under `/teams`: CRUD plus the shared opponent pool.

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
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> PaginatedTeams:
    """List teams, ordered by name. Paginated: `limit` is 1-200 (default 20) and `offset`
    starts at 0; the response carries `total` so clients can page.
    """
    items, total = await service.list_teams(
        session, owner_id=user_id, limit=limit, offset=offset
    )
    return PaginatedTeams(
        items=[TeamResponse.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    body: TeamCreate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamResponse:
    """Create a team. `is_public` (default true) lists it in the opponent pool."""
    team = await service.create_team(
        session, name=body.name, owner_id=user_id, is_public=body.is_public
    )
    return TeamResponse.model_validate(team)


# Registered before /{team_id} so "pool" isn't swallowed as a team_id path param
@router.get("/pool", response_model=list[TeamPoolItem])
async def search_teams_pool(
    search: Annotated[
        str | None,
        Query(max_length=120, description="Filter by team name (literal match)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
) -> list[TeamPoolItem]:
    """Search the shared opponent pool. Only public teams are returned, and only their
    `id` and `name`. `search` is a literal, case-insensitive substring.
    """
    teams = await service.search_teams_pool(session, search=search, limit=limit)
    return [TeamPoolItem.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamResponse:
    """Get one team by id (404 if unknown)."""
    team = await service.get_team_or_404(session, team_id=team_id, owner_id=user_id)
    return TeamResponse.model_validate(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    body: TeamUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamResponse:
    """Rename a team (404 if unknown)."""
    team = await service.update_team(
        session, team_id=team_id, name=body.name, owner_id=user_id
    )
    return TeamResponse.model_validate(team)


@router.delete("/{team_id}", response_model=TeamDeleteResponse)
async def delete_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamDeleteResponse:
    """Delete a team. Returns 409 while players are still on its roster; saved lineups that
    mention the team are unaffected because they store copies.
    """
    return await service.delete_team(session, team_id=team_id, owner_id=user_id)
