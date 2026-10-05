"""Request and response shapes for `/lineups/saved`, including the rules that keep a snapshot
unambiguous: exactly one of source id / free text per field, unique cap and NSSZ numbers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from lineup.common.types import (
    CleanStr50,
    CleanStr100,
    CleanStr200,
    OptionalCleanStr50,
    OptionalCleanStr120,
    OptionalCleanStr200,
)


class SavedLineupPlayerCreate(BaseModel):
    """One player slot: reference an existing roster player (whose current
    name/NSSZ number is frozen at save time) or supply free text directly, never both."""

    source_player_id: uuid.UUID | None = None
    name: OptionalCleanStr200 = None
    nssz_number: OptionalCleanStr50 = None
    cap_number: int = Field(..., ge=1, le=15)

    @model_validator(mode="after")
    def require_identity(self) -> "SavedLineupPlayerCreate":
        """Enforce "exactly one of `source_player_id` or (`name` and `nssz_number`)"."""
        free_text = self.name is not None or self.nssz_number is not None
        if self.source_player_id is not None and free_text:
            raise ValueError(
                "Send either source_player_id or name and nssz_number, not both"
            )
        if self.source_player_id is None and not (self.name and self.nssz_number):
            raise ValueError(
                "Either source_player_id or both name and nssz_number must be provided"
            )
        return self


class SavedLineupCreate(BaseModel):
    """Body for saving a lineup.

    `team_id` is the workspace the lineup is saved in (a team you belong to); every member of
    that team can then see it. It is independent of `source_team_id`, which only says where the
    team *name* comes from. Team and opponent each need either a `source_*_id` or a name, never both. `match_name`
    defaults to "<team> - <opponent>". Blank optional values count as not provided. Cap numbers
    must be unique, and no roster player may appear twice.
    """

    team_id: uuid.UUID
    source_team_id: uuid.UUID | None = None
    team_name: OptionalCleanStr120 = None
    source_opponent_id: uuid.UUID | None = None
    opponent_name: OptionalCleanStr120 = None
    match_name: OptionalCleanStr200 = None
    division: CleanStr100
    cap: Literal["Fehér", "Kék"]
    date: CleanStr50
    coach: CleanStr200
    doctor: OptionalCleanStr200 = None
    assistant_coach: OptionalCleanStr200 = None
    team_leader: OptionalCleanStr200 = None
    ball_thrower: OptionalCleanStr200 = None
    players: list[SavedLineupPlayerCreate] = Field(..., min_length=1, max_length=15)

    @field_validator("players")
    @classmethod
    def cap_numbers_unique(
        cls, players: list[SavedLineupPlayerCreate]
    ) -> list[SavedLineupPlayerCreate]:
        """Reject two players sharing a cap number."""
        cap_numbers = [p.cap_number for p in players]
        if len(cap_numbers) != len(set(cap_numbers)):
            raise ValueError("Cap numbers within a lineup must be unique")
        return players

    @field_validator("players")
    @classmethod
    def source_player_ids_unique(
        cls, players: list[SavedLineupPlayerCreate]
    ) -> list[SavedLineupPlayerCreate]:
        """Reject the same roster player appearing in two slots."""
        source_ids = [
            p.source_player_id for p in players if p.source_player_id is not None
        ]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("A player cannot appear more than once in a lineup")
        return players

    @model_validator(mode="after")
    def require_team_identity(self) -> "SavedLineupCreate":
        """Enforce "exactly one of source id or name" for both the team and the opponent."""
        for source_id, name, label in (
            (self.source_team_id, self.team_name, "team"),
            (self.source_opponent_id, self.opponent_name, "opponent"),
        ):
            if source_id is None and name is None:
                raise ValueError(
                    f"Either source_{label}_id or {label}_name must be provided"
                )
            if source_id is not None and name is not None:
                raise ValueError(
                    f"Send either source_{label}_id or {label}_name, not both"
                )
        return self


class SavedLineupPlayerResponse(BaseModel):
    """A player slot of a saved lineup, as frozen when it was saved."""

    id: uuid.UUID
    cap_number: int
    name: str
    nssz_number: str
    source_player_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class SavedLineupResponse(BaseModel):
    """A saved lineup as returned by the API. All text is the frozen copy; `source_*_id`
    fields are soft references and become null if the source is deleted. `team_id` is the
    workspace the lineup lives in.
    """

    id: uuid.UUID
    team_id: uuid.UUID
    team_name: str
    opponent_name: str
    match_name: str
    division: str
    cap: str
    date: str
    coach: str
    doctor: str | None
    assistant_coach: str | None
    team_leader: str | None
    ball_thrower: str | None
    source_team_id: uuid.UUID | None
    source_opponent_id: uuid.UUID | None
    players: list[SavedLineupPlayerResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedSavedLineups(BaseModel):
    """One page of saved lineups plus the total number of matching lineups."""

    items: list[SavedLineupResponse]
    total: int
    limit: int
    offset: int
