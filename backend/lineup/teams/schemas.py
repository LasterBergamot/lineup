"""Request and response shapes for `/teams` (what the API accepts and returns)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr120
from lineup.db.models import Team


class TeamCreate(BaseModel):
    """Body for creating a team. The name is trimmed and must not be blank or contain control
    characters.
    """

    name: CleanStr120
    is_public: bool = True


class TeamUpdate(BaseModel):
    """Body for updating a team (owners only). `name` is always required; `is_public` lists or
    unlists the team in the opponent directory and is left unchanged when omitted."""

    name: CleanStr120
    is_public: bool | None = None


class TeamResponse(BaseModel):
    """A team as returned by the API, from the signed-in caller's point of view.

    `role` is the caller's role in the team (`owner` or `member`); `created_by` is who created
    it (audit only, it grants nothing). `is_public` means "listed in the opponent directory".
    """

    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    is_public: bool
    created_at: datetime
    role: str

    @classmethod
    def from_team(cls, team: Team, role: str) -> "TeamResponse":
        """Build the response from an ORM team and the caller's role in it."""
        return cls(
            id=team.id,
            name=team.name,
            created_by=team.created_by,
            is_public=team.is_public,
            created_at=team.created_at,
            role=role,
        )


class TeamDeleteResponse(BaseModel):
    """Confirmation returned after a team is deleted."""

    id: uuid.UUID
    name: str
    deleted: bool


class TeamPoolItem(BaseModel):
    """Entry of the shared opponent directory: `id` and `name` and nothing else, on purpose.
    Listing a team must never reveal its roster, members or lineups."""

    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class PaginatedTeams(BaseModel):
    """One page of teams plus the total number of teams."""

    items: list[TeamResponse]
    total: int
    limit: int
    offset: int
