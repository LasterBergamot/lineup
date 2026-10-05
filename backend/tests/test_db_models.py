import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import (
    Player,
    SavedLineup,
    Team,
    TeamInvitation,
    TeamMember,
    TeamRole,
    _utcnow,
)


def test_utcnow_is_naive_utc():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    value = _utcnow()
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert value.tzinfo is None
    assert before <= value <= after


@pytest.mark.parametrize(
    ("model", "column"),
    [
        (Team, "created_at"),
        (Player, "created_at"),
        (SavedLineup, "created_at"),
        (TeamMember, "joined_at"),
        (TeamInvitation, "created_at"),
    ],
)
def test_timestamp_defaults_are_naive(model, column):
    # Postgres (asyncpg) rejects an aware datetime for a TIMESTAMP WITHOUT TIME ZONE
    # column; SQLite hides the problem by dropping tzinfo, so assert it directly.
    default = model.__table__.c[column].default

    assert default.arg(None).tzinfo is None


async def _team(db_session: AsyncSession) -> Team:
    team = Team(id=uuid.uuid4(), name="T", created_by=uuid.uuid4(), is_public=True)
    db_session.add(team)
    await db_session.commit()
    return team


def _invitation(team_id: uuid.UUID, code_hash: str = "a" * 64, **kw) -> TeamInvitation:
    return TeamInvitation(
        team_id=team_id,
        invited_by=uuid.uuid4(),
        invite_code_hash=code_hash,
        expires_at=_utcnow() + timedelta(hours=24),
        **kw,
    )


class TestTeamMember:
    async def test_role_defaults_to_member(self, db_session: AsyncSession):
        team = await _team(db_session)
        db_session.add(TeamMember(team_id=team.id, user_id=uuid.uuid4()))
        await db_session.commit()
        member = (await db_session.execute(select(TeamMember))).scalar_one()
        assert member.role == TeamRole.MEMBER.value
        assert member.joined_at is not None

    async def test_a_user_can_join_a_team_only_once(self, db_session: AsyncSession):
        team = await _team(db_session)
        user = uuid.uuid4()
        db_session.add(TeamMember(team_id=team.id, user_id=user))
        await db_session.commit()
        db_session.add(TeamMember(team_id=team.id, user_id=user, role="owner"))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_unknown_roles_are_rejected_by_the_database(
        self, db_session: AsyncSession
    ):
        team = await _team(db_session)
        db_session.add(TeamMember(team_id=team.id, user_id=uuid.uuid4(), role="admin"))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_members_go_with_their_team(self, db_session: AsyncSession):
        team = await _team(db_session)
        db_session.add(TeamMember(team_id=team.id, user_id=uuid.uuid4()))
        await db_session.commit()
        await db_session.delete(team)
        await db_session.commit()
        assert (await db_session.execute(select(TeamMember))).first() is None

    async def test_membership_needs_an_existing_team(self, db_session: AsyncSession):
        db_session.add(TeamMember(team_id=uuid.uuid4(), user_id=uuid.uuid4()))
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestTeamInvitation:
    async def test_defaults_to_a_member_invite_that_is_not_revoked(
        self, db_session: AsyncSession
    ):
        team = await _team(db_session)
        db_session.add(_invitation(team.id))
        await db_session.commit()
        invitation = (await db_session.execute(select(TeamInvitation))).scalar_one()
        assert invitation.role == "member"
        assert invitation.revoked_at is None
        assert invitation.email is None

    async def test_code_hashes_are_unique(self, db_session: AsyncSession):
        team = await _team(db_session)
        db_session.add(_invitation(team.id))
        await db_session.commit()
        db_session.add(_invitation(team.id))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_unknown_roles_are_rejected_by_the_database(
        self, db_session: AsyncSession
    ):
        team = await _team(db_session)
        db_session.add(_invitation(team.id, role="admin"))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_invitations_go_with_their_team(self, db_session: AsyncSession):
        team = await _team(db_session)
        db_session.add(_invitation(team.id))
        await db_session.commit()
        await db_session.delete(team)
        await db_session.commit()
        assert (await db_session.execute(select(TeamInvitation))).first() is None
