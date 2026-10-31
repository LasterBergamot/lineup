"""Database access for invitation links: the only place that writes invitation queries.

Only the SHA-256 hash of a code is ever stored or queried. Authorisation (who may create, list or
revoke) is the service's job; these functions just read and write rows.
"""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Team, TeamInvitation


def hash_code(code: str) -> str:
    """SHA-256 hex digest of an invite code: what the database stores and looks up. The codes
    carry 256 bits of randomness, so a plain (unsalted, fast) hash is enough and keeps the
    lookup an indexed equality."""
    return hashlib.sha256(code.encode()).hexdigest()


async def create_invitation(
    session: AsyncSession,
    team_id: uuid.UUID,
    invited_by: uuid.UUID,
    invited_by_name: str | None,
    code_hash: str,
    role: str,
    expires_at: datetime,
) -> TeamInvitation:
    """Insert an invitation and commit; returns it with its generated fields loaded."""
    invitation = TeamInvitation(
        id=uuid.uuid4(),
        team_id=team_id,
        invited_by=invited_by,
        invited_by_name=invited_by_name,
        invite_code_hash=code_hash,
        role=role,
        expires_at=expires_at,
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)
    return invitation


async def purge_expired(session: AsyncSession, cutoff: datetime) -> None:
    """Delete invitations of every team that expired before `cutoff`, and commit. A revoked link
    is removed the same way once its own expiry is past the cutoff. This is the retention rule
    for invitation data (incl. the inviter's name)."""
    await session.execute(
        delete(TeamInvitation).where(TeamInvitation.expires_at < cutoff)
    )
    await session.commit()


async def list_active(
    session: AsyncSession, team_id: uuid.UUID, now: datetime
) -> list[TeamInvitation]:
    """The team's links that still work (not revoked, not expired), newest first."""
    query = (
        select(TeamInvitation)
        .where(
            TeamInvitation.team_id == team_id,
            TeamInvitation.revoked_at.is_(None),
            TeamInvitation.expires_at > now,
        )
        .order_by(TeamInvitation.created_at.desc(), TeamInvitation.id)
    )
    return list((await session.execute(query)).scalars().all())


async def get_for_team(
    session: AsyncSession, team_id: uuid.UUID, invitation_id: uuid.UUID
) -> TeamInvitation | None:
    """One invitation of this team, or `None` (also when the id belongs to another team)."""
    result = await session.execute(
        select(TeamInvitation).where(
            TeamInvitation.id == invitation_id, TeamInvitation.team_id == team_id
        )
    )
    return result.scalar_one_or_none()


async def revoke(
    session: AsyncSession, invitation: TeamInvitation, now: datetime
) -> None:
    """Mark the invitation revoked and commit. Revoking twice keeps the first timestamp."""
    if invitation.revoked_at is None:
        invitation.revoked_at = now
        await session.commit()


async def get_with_team_by_hash(
    session: AsyncSession, code_hash: str
) -> tuple[TeamInvitation, Team] | None:
    """The invitation with this code hash and its team, or `None` if no such link exists."""
    result = await session.execute(
        select(TeamInvitation, Team)
        .join(Team, Team.id == TeamInvitation.team_id)
        .where(TeamInvitation.invite_code_hash == code_hash)
    )
    row = result.one_or_none()
    return None if row is None else (row[0], row[1])
