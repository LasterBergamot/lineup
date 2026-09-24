from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    nssz_number: str = Field(..., min_length=1, max_length=50)
    team_id: uuid.UUID | None = None


class PlayerUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    nssz_number: str = Field(..., min_length=1, max_length=50)
    team_id: uuid.UUID | None = None


class PlayerResponse(BaseModel):
    id: uuid.UUID
    name: str
    nssz_number: str
    team_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPlayers(BaseModel):
    items: list[PlayerResponse]
    total: int
    limit: int
    offset: int
