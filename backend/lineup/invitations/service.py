"""Business rules for invitation links, between the router (HTTP) and the repository (SQL).

A link is a multi-use, expiring, revocable way into a team (`PLAN.md` section 6.3). Failures:
`404` for a code that does not exist (and for teams/invitations the caller cannot see), `410` for
a link that existed but is expired or revoked, `403` for a member who is not an owner.
"""

import os
import secrets
import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Team, TeamInvitation, TeamRole, _utcnow
from lineup.invitations import repository
from lineup.invitations.schemas import InvitationCreated, InvitationPreview
from lineup.teams import repository as team_repository
from lineup.teams import service as team_service

CODE_BYTES = 32  # 256 bits of randomness
DEFAULT_APP_BASE_URL = "http://localhost:5173"
# An expired link stays a week so its owner and a late guest still get "expired" (410) rather
# than "unknown" (404); then it is deleted, which is the retention rule for invitation data.
PURGE_GRACE = timedelta(days=7)


def app_base_url() -> str:
    """The web app's origin, which the invite `url` points at: `APP_BASE_URL` (no trailing
    slash), or the local Vite dev server when unset."""
    return os.getenv("APP_BASE_URL", "").strip().rstrip("/") or DEFAULT_APP_BASE_URL


async def create_invitation(
    session: AsyncSession,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    display_name: str | None,
    expires_in_hours: int,
) -> InvitationCreated:
    """Make a new member-role link for the team (owner only: 404/403 otherwise).

    The plaintext code exists only in the returned object; the database gets its hash. Expired
    links past the grace period are deleted on the way.
    """
    await team_service.get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    now = _utcnow()
    await repository.purge_expired(session, now - PURGE_GRACE)
    code = secrets.token_urlsafe(CODE_BYTES)
    invitation = await repository.create_invitation(
        session,
        team_id=team_id,
        invited_by=user_id,
        invited_by_name=display_name,
        code_hash=repository.hash_code(code),
        role=TeamRole.MEMBER.value,
        expires_at=now + timedelta(hours=expires_in_hours),
    )
    return InvitationCreated(
        id=invitation.id,
        code=code,
        url=f"{app_base_url()}/join/{code}",
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


async def list_invitations(
    session: AsyncSession, team_id: uuid.UUID, user_id: uuid.UUID
) -> list[TeamInvitation]:
    """The team's links that still work, newest first (owner only: 404/403 otherwise)."""
    await team_service.get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    now = _utcnow()
    await repository.purge_expired(session, now - PURGE_GRACE)
    return await repository.list_active(session, team_id=team_id, now=now)


async def revoke_invitation(
    session: AsyncSession,
    team_id: uuid.UUID,
    invitation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Stop a link from working (owner only). 404 when the invitation is unknown or belongs to
    another team. Revoking an already revoked link is fine."""
    await team_service.get_owned_team_or_404(session, team_id=team_id, user_id=user_id)
    invitation = await repository.get_for_team(
        session, team_id=team_id, invitation_id=invitation_id
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    await repository.revoke(session, invitation, now=_utcnow())


async def _usable_invitation(
    session: AsyncSession, code: str
) -> tuple[TeamInvitation, Team]:
    """Look the code up by hash. 404 if unknown, 410 if revoked or expired."""
    found = await repository.get_with_team_by_hash(session, repository.hash_code(code))
    if found is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    invitation, _team = found
    if invitation.revoked_at is not None or invitation.expires_at <= _utcnow():
        raise HTTPException(status_code=410, detail="Invitation expired or revoked")
    return found


async def preview_invitation(session: AsyncSession, code: str) -> InvitationPreview:
    """What the join page shows before sign-in: team name, inviter's display name, expiry."""
    invitation, team = await _usable_invitation(session, code)
    return InvitationPreview(
        team_name=team.name,
        invited_by_name=invitation.invited_by_name,
        expires_at=invitation.expires_at,
    )


async def accept_invitation(
    session: AsyncSession,
    code: str,
    user_id: uuid.UUID,
    display_name: str | None = None,
) -> tuple[Team, str]:
    """Join the team behind `code` and return it with the caller's role; the new membership
    records `display_name` so teammates can tell who joined.

    Idempotent: someone who is already a member keeps their role (an owner is never demoted by
    opening a member link). 404/410 as for the preview.
    """
    invitation, team = await _usable_invitation(session, code)
    team_id = team.id  # read now: a rollback below expires the ORM objects
    membership = await team_repository.get_membership(
        session, team_id=team_id, user_id=user_id
    )
    if membership is not None:
        return team, membership.role
    await team_repository.add_member(
        session,
        team_id=team_id,
        user_id=user_id,
        role=invitation.role,
        display_name=display_name,
    )
    # Re-read instead of trusting the insert: a double click can lose the race (the other
    # request already inserted the row, and the failed insert rolled this session back), and
    # the team may have been deleted meanwhile.
    joined = await team_repository.get_team(session, team_id=team_id, user_id=user_id)
    if joined is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return joined
