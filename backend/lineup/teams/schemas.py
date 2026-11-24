"""Request and response shapes for `/teams` (what the API accepts and returns)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from lineup.common.types import CleanStr100, CleanStr120
from lineup.db.models import Team


class TeamCreate(BaseModel):
    """Body for creating a team. `division` is the team's usual division (optional, at most 100
    characters), which the lineup creator pre-fills. The name is trimmed and must not be blank or contain control
    characters.
    """

    name: CleanStr120
    is_public: bool = True
    division: CleanStr100 | None = None


class TeamUpdate(BaseModel):
    """Body for updating a team (owners only). `name` is always required; `is_public` lists or
    unlists the team in the opponent directory and `division` sets its default division; both are
    left unchanged when omitted (so a division cannot be cleared once set, only replaced)."""

    name: CleanStr120
    is_public: bool | None = None
    division: CleanStr100 | None = None


class TeamResponse(BaseModel):
    """A team as returned by the API, from the signed-in caller's point of view.

    `role` is the caller's role in the team (`owner` or `member`); `created_by` is who created
    it (audit only, it grants nothing). `is_public` means "listed in the opponent directory".
    `division` is the team's default division (`null` when unset), used to pre-fill new lineups.
    """

    id: uuid.UUID
    name: str
    created_by: uuid.UUID
    is_public: bool
    division: str | None
    created_at: datetime
    role: str

    @classmethod
    def from_team(cls, team: Team, role: str) -> TeamResponse:
        """Build the response from an ORM team and the caller's role in it."""
        return cls(
            id=team.id,
            name=team.name,
            created_by=team.created_by,
            is_public=team.is_public,
            division=team.division,
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


class MemberResponse(BaseModel):
    """One member of a team: id, role, join date and, when known, their name. `display_name` is
    the Google name the member's own token carried the last time they used the app; it is `null`
    for someone who has not opened the app since names were introduced, so show a fallback
    such as "Member 2". No e-mail addresses are stored. `is_you` marks the caller's own row so a
    client can show "(you)" and a Leave button."""

    user_id: uuid.UUID
    role: str
    joined_at: datetime
    display_name: str | None
    is_you: bool


class OwnershipTransfer(BaseModel):
    """Body for handing a team over: the member who becomes its owner."""

    user_id: uuid.UUID
