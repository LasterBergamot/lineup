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
        cap_numbers = [p.cap_number for p in players]
        if len(cap_numbers) != len(set(cap_numbers)):
            raise ValueError("Cap numbers within a lineup must be unique")
        return players

    @field_validator("players")
    @classmethod
    def source_player_ids_unique(
        cls, players: list[SavedLineupPlayerCreate]
    ) -> list[SavedLineupPlayerCreate]:
        source_ids = [
            p.source_player_id for p in players if p.source_player_id is not None
        ]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("A player cannot appear more than once in a lineup")
        return players

    @model_validator(mode="after")
    def require_team_identity(self) -> "SavedLineupCreate":
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
    id: uuid.UUID
    cap_number: int
    name: str
    nssz_number: str
    source_player_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class SavedLineupResponse(BaseModel):
    id: uuid.UUID
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
    items: list[SavedLineupResponse]
    total: int
    limit: int
    offset: int
