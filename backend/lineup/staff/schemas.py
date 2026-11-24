"""Request and response shapes for `/teams/{team_id}/staff`."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from lineup.common.types import CleanStr200
from lineup.db.models import StaffRole


class StaffWrite(BaseModel):
    """Body for creating a staff entry or replacing one (`PUT` overwrites every field).

    `name` is trimmed, must not be blank or contain control characters. It is stored as a copy:
    when you pick a roster player, send their name here and their id as `source_player_id`; the
    entry then keeps the name even after the player is deleted or renamed.
    """

    role: StaffRole = Field(description="Which staff role this person fills.")
    name: CleanStr200
    source_player_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "The roster player this entry was picked from, or omitted for a typed-in name. "
            "Must be a player of this same team, otherwise 404. The name is not kept in sync "
            "with the player."
        ),
    )
    is_default: bool = Field(
        default=False,
        description=(
            "Make this the team's default for its role. The previous default of that role, "
            "if any, stops being the default in the same transaction."
        ),
    )


class StaffResponse(BaseModel):
    """A staff entry as returned by the API."""

    id: uuid.UUID
    team_id: uuid.UUID
    role: StaffRole
    name: str
    source_player_id: uuid.UUID | None = Field(
        description="The roster player it was picked from; `null` for a typed-in name or once that player was deleted."
    )
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}
