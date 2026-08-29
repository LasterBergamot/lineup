from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class PlayerRequest(BaseModel):
    cap_number: int = Field(..., ge=1, le=15)
    name: str = Field(..., min_length=1)
    nssz_number: str = Field(..., min_length=1)


class LineupRequest(BaseModel):
    match: str = Field(..., min_length=1)
    division: str = Field(..., min_length=1)
    team_name: str = Field(..., min_length=1)
    cap: Literal["Fehér", "Kék"]
    date: str = Field(..., min_length=1)
    coach: str = Field(..., min_length=1)
    doctor: str = Field(..., min_length=1)
    assistant_coach: str = Field(..., min_length=1)
    team_leader: str = Field(..., min_length=1)
    ball_thrower: str = Field(..., min_length=1)
    players: List[PlayerRequest] = Field(..., min_length=1, max_length=15)

    @field_validator("players")
    @classmethod
    def cap_numbers_unique(cls, players: List[PlayerRequest]) -> List[PlayerRequest]:
        cap_numbers = [p.cap_number for p in players]
        if len(cap_numbers) != len(set(cap_numbers)):
            raise ValueError("Player cap numbers must be unique")
        return players
