from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SavedLineupPlayerCreate(BaseModel):
    """One player slot: reference an existing roster player (whose current
    name/NSSZ number is frozen at save time) or supply free text directly."""

    source_player_id: uuid.UUID | None = None
    name: str | None = Field(None, max_length=200)
    nssz_number: str | None = Field(None, max_length=50)
    cap_number: int = Field(..., ge=1, le=15)

    @model_validator(mode="after")
    def require_identity(self) -> "SavedLineupPlayerCreate":
        if self.source_player_id is None and not (self.name and self.nssz_number):
            raise ValueError(
                "Either source_player_id or both name and nssz_number must be provided"
            )
        return self


class SavedLineupCreate(BaseModel):
    source_team_id: uuid.UUID | None = None
    team_name: str | None = Field(None, max_length=120)
    source_opponent_id: uuid.UUID | None = None
    opponent_name: str | None = Field(None, max_length=120)
    match_name: str | None = Field(None, max_length=200)
    division: str = Field(..., min_length=1, max_length=100)
    cap: Literal["Fehér", "Kék"]
    date: str = Field(..., min_length=1, max_length=50)
    coach: str = Field(..., min_length=1, max_length=200)
    doctor: str | None = Field(None, max_length=200)
    assistant_coach: str | None = Field(None, max_length=200)
    team_leader: str | None = Field(None, max_length=200)
    ball_thrower: str | None = Field(None, max_length=200)
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
        if self.source_team_id is None and not self.team_name:
            raise ValueError("Either source_team_id or team_name must be provided")
        if self.source_opponent_id is None and not self.opponent_name:
            raise ValueError(
                "Either source_opponent_id or opponent_name must be provided"
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
