from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr120


class TeamCreate(BaseModel):
    name: CleanStr120
    is_public: bool = True


class TeamUpdate(BaseModel):
    name: CleanStr120


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID | None
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamDeleteResponse(BaseModel):
    id: uuid.UUID
    name: str
    deleted: bool


class TeamPoolItem(BaseModel):
    """Lightweight entry for the shared opponent pool — id + name only."""

    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class PaginatedTeams(BaseModel):
    items: list[TeamResponse]
    total: int
    limit: int
    offset: int
