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
        int, Query(ge=0, description="Max items to return. 0 = no limit.")
    ] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> PaginatedTeams:
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
    team = await service.create_team(
        session, name=body.name, owner_id=user_id, is_public=body.is_public
    )
    return TeamResponse.model_validate(team)


# Registered before /{team_id} so "pool" isn't swallowed as a team_id path param
@router.get("/pool", response_model=list[TeamPoolItem])
async def search_teams_pool(
    search: Annotated[str | None, Query(description="Filter by team name")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
) -> list[TeamPoolItem]:
    teams = await service.search_teams_pool(session, search=search, limit=limit)
    return [TeamPoolItem.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamResponse:
    team = await service.get_team_or_404(session, team_id=team_id, owner_id=user_id)
    return TeamResponse.model_validate(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    body: TeamUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_current_user_id),
) -> TeamResponse:
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
    return await service.delete_team(session, team_id=team_id, owner_id=user_id)
