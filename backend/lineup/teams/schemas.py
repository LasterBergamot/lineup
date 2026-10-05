"""Request and response shapes for `/teams` (what the API accepts and returns)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr120


class TeamCreate(BaseModel):
    """Body for creating a team. The name is trimmed and must not be blank or contain control
    characters.
    """

    name: CleanStr120
    is_public: bool = True


class TeamUpdate(BaseModel):
    """Body for renaming a team."""

    name: CleanStr120


class TeamResponse(BaseModel):
    """A team as returned by the API."""

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamDeleteResponse(BaseModel):
    """Confirmation returned after a team is deleted."""

    id: uuid.UUID
    name: str
    deleted: bool


class TeamPoolItem(BaseModel):
    """Lightweight entry for the shared opponent pool — id + name only."""

    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class PaginatedTeams(BaseModel):
    """One page of teams plus the total number of teams."""

    items: list[TeamResponse]
    total: int
    limit: int
    offset: int
