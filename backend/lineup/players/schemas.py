from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr50, CleanStr200


class PlayerCreate(BaseModel):
    name: CleanStr200
    nssz_number: CleanStr50
    team_id: uuid.UUID | None = None


class PlayerUpdate(BaseModel):
    name: CleanStr200
    nssz_number: CleanStr50
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
