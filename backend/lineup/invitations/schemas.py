"""Request and response shapes for invitation links (what the API accepts and returns)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from lineup.db.models import TeamInvitation


class InvitationCreate(BaseModel):
    """Body for creating an invite link. The link stops working after `expires_in_hours`
    (2, 24 or 72; default 24): a short life limits the damage if it is forwarded further than
    intended. Anyone who opens it while signed in joins as a member."""

    expires_in_hours: Literal[2, 24, 72] = 24


class InvitationCreated(BaseModel):
    """A freshly created invite link. `code` and `url` are shown **only in this response**: the
    server keeps just a hash, so they cannot be shown again. Send `url` to the person you want
    to invite."""

    id: uuid.UUID
    code: str
    url: str
    role: str
    expires_at: datetime


class InvitationResponse(BaseModel):
    """An invite link that still works, as listed to the team's owners. It carries no code (that
    was shown once, at creation); `id` is what you pass to revoke it."""

    id: uuid.UUID
    role: str
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_invitation(cls, invitation: TeamInvitation) -> "InvitationResponse":
        """Build the response from an ORM invitation."""
        return cls(
            id=invitation.id,
            role=invitation.role,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
        )


class InvitationPreview(BaseModel):
    """What anyone holding a link may see before signing in: the team's name, the display name of
    whoever created the link (if their sign-in provided one) and when the link expires. Nothing
    else about the team or its members."""

    team_name: str
    invited_by_name: str | None
    expires_at: datetime
