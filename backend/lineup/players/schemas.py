"""Request and response shapes for `/players`."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr50, CleanStr200


class PlayerCreate(BaseModel):
    """Body for creating a player. Text is trimmed, must not be blank or contain control
    characters; `team_id` is the roster to add the player to and must be a team you belong to.
    """

    name: CleanStr200
    nssz_number: CleanStr50
    team_id: uuid.UUID


class PlayerUpdate(BaseModel):
    """Body for replacing a player's data (all fields are overwritten, including `team_id`,
    which may move the player to another team you belong to)."""

    name: CleanStr200
    nssz_number: CleanStr50
    team_id: uuid.UUID


class PlayerResponse(BaseModel):
    """A player as returned by the API."""

    id: uuid.UUID
    name: str
    nssz_number: str
    team_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPlayers(BaseModel):
    """One page of players plus the total number of matching players."""

    items: list[PlayerResponse]
    total: int
    limit: int
    offset: int
