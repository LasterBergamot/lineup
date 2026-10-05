from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class PlayerRequest(BaseModel):
    cap_number: int = Field(..., ge=1, le=15)
    name: str = Field(..., min_length=1, max_length=200)
    nssz_number: str = Field(..., min_length=1, max_length=50)


class LineupRequest(BaseModel):
    match: str = Field(..., min_length=1, max_length=200)
    division: str = Field(..., min_length=1, max_length=100)
    team_name: str = Field(..., min_length=1, max_length=120)
    cap: Literal["Fehér", "Kék"]
    date: str = Field(..., min_length=1, max_length=50)
    coach: str = Field(..., min_length=1, max_length=200)
    doctor: str = Field(..., min_length=1, max_length=200)
    assistant_coach: str = Field(..., min_length=1, max_length=200)
    team_leader: str = Field(..., min_length=1, max_length=200)
    ball_thrower: str = Field(..., min_length=1, max_length=200)
    players: List[PlayerRequest] = Field(..., min_length=1, max_length=15)

    @field_validator("players")
    @classmethod
    def cap_numbers_unique(cls, players: List[PlayerRequest]) -> List[PlayerRequest]:
        cap_numbers = [p.cap_number for p in players]
        if len(cap_numbers) != len(set(cap_numbers)):
            raise ValueError("Player cap numbers must be unique")
        return players
