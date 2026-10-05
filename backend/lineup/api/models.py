"""Request bodies for the one-off `POST /lineups` endpoint.

These are validated by Pydantic, so bad input becomes a 422 before any document code runs.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from lineup.common.types import CleanStr50, CleanStr100, CleanStr120, CleanStr200


class PlayerRequest(BaseModel):
    """One player on the lineup sheet."""

    cap_number: int = Field(..., ge=1, le=15)
    name: CleanStr200
    nssz_number: CleanStr50


class LineupRequest(BaseModel):
    """Everything needed to fill one lineup sheet (no database involved).

    Text fields are trimmed, must not be empty and have a maximum length. `players` holds 1 to 15
    entries with unique cap numbers (1-15) and unique NSSZ numbers.
    """

    match: CleanStr200
    division: CleanStr100
    team_name: CleanStr120
    cap: Literal["Fehér", "Kék"]
    date: CleanStr50
    coach: CleanStr200
    doctor: CleanStr200
    assistant_coach: CleanStr200
    team_leader: CleanStr200
    ball_thrower: CleanStr200
    players: List[PlayerRequest] = Field(..., min_length=1, max_length=15)

    @field_validator("players")
    @classmethod
    def cap_numbers_unique(cls, players: List[PlayerRequest]) -> List[PlayerRequest]:
        """Reject two players sharing a cap number."""
        cap_numbers = [p.cap_number for p in players]
        if len(cap_numbers) != len(set(cap_numbers)):
            raise ValueError("Player cap numbers must be unique")
        return players

    @field_validator("players")
    @classmethod
    def nssz_numbers_unique(cls, players: List[PlayerRequest]) -> List[PlayerRequest]:
        """Reject two players with the same NSSZ number (compared case-insensitively)."""
        nssz_numbers = [p.nssz_number.casefold() for p in players]
        if len(nssz_numbers) != len(set(nssz_numbers)):
            raise ValueError("Player NSSZ numbers must be unique")
        return players
