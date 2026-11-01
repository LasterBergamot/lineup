import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import (
    LineupPlayerSnapshot,
    Player,
    SavedLineup,
    Team,
    TeamInvitation,
    TeamMember,
    TeamRole,
    _utcnow,
)
from lineup.db.types import UtcDateTime


def test_utcnow_is_aware_utc():
    before = datetime.now(UTC)
    value = _utcnow()
    after = datetime.now(UTC)

    assert value.utcoffset() == timedelta(0)
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
def test_timestamp_defaults_are_aware_and_have_a_server_default(model, column):
    # The columns are timestamptz (`UtcDateTime`), which rejects a naive value, and a row
    # inserted outside the app (Supabase Studio) must still get a timestamp.
    col = model.__table__.c[column]

    assert col.default.arg(None).tzinfo is not None
    assert col.server_default is not None


@pytest.mark.parametrize(
    ("model", "column"),
    [
        (Team, "is_public"),
        (TeamMember, "role"),
        (TeamInvitation, "role"),
    ],
)
def test_flags_and_roles_have_server_defaults(model, column):
    assert model.__table__.c[column].server_default is not None


async def test_a_row_inserted_without_defaults_gets_them(db_session: AsyncSession):
    # What a hand-written INSERT in Supabase Studio looks like: only the required columns.
    team_id = uuid.uuid4()
    await db_session.execute(
        text("INSERT INTO teams (id, name, created_by) VALUES (:id, 'T', :by)"),
        {"id": team_id.hex, "by": uuid.uuid4().hex},
    )
    await db_session.execute(
        text("INSERT INTO team_members (team_id, user_id) VALUES (:id, :u)"),
        {"id": team_id.hex, "u": uuid.uuid4().hex},
    )
    await db_session.commit()

    team = (await db_session.execute(select(Team))).scalar_one()
    member = (await db_session.execute(select(TeamMember))).scalar_one()
    assert team.is_public is True
    assert team.created_at.tzinfo is not None
    assert member.role == "member"
    assert member.joined_at.tzinfo is not None


class TestUtcDateTime:
    def test_aware_values_are_stored_as_utc(self):
        plus_two = datetime(2026, 11, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))

        stored = UtcDateTime().process_bind_param(plus_two, None)

        assert stored == datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
        assert stored.utcoffset() == timedelta(0)

    def test_a_naive_value_is_refused(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            UtcDateTime().process_bind_param(datetime(2026, 11, 1, 12, 0), None)

    def test_none_passes_through_both_ways(self):
        assert UtcDateTime().process_bind_param(None, None) is None
        assert UtcDateTime().process_result_value(None, None) is None

    def test_a_value_without_a_zone_is_read_back_as_utc(self):
        # SQLite drops the zone.
        read = UtcDateTime().process_result_value(datetime(2026, 11, 1, 10, 0), None)

        assert read == datetime(2026, 11, 1, 10, 0, tzinfo=UTC)

    def test_an_aware_value_is_read_back_in_utc(self):
        stored = datetime(2026, 11, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))

        read = UtcDateTime().process_result_value(stored, None)

        assert read.utcoffset() == timedelta(0)
        assert read == stored


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
        assert invitation.invited_by_name is None

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


class TestLineupPlayerSnapshot:
    async def _lineup(self, db_session: AsyncSession) -> SavedLineup:
        team = await _team(db_session)
        lineup = SavedLineup(
            team_id=team.id,
            team_name="T",
            opponent_name="O",
            match_name="T - O",
            division="OB I.",
            cap="Fehér",
            date="2026. 11. 01.",
            coach="C",
            created_by=uuid.uuid4(),
        )
        db_session.add(lineup)
        await db_session.commit()
        return lineup

    def _snapshot(self, lineup_id: uuid.UUID, cap_number: int) -> LineupPlayerSnapshot:
        return LineupPlayerSnapshot(
            saved_lineup_id=lineup_id,
            cap_number=cap_number,
            name="P",
            nssz_number="N1",
        )

    async def test_a_cap_number_can_be_used_once_per_lineup(
        self, db_session: AsyncSession
    ):
        lineup = await self._lineup(db_session)
        db_session.add(self._snapshot(lineup.id, 1))
        await db_session.commit()

        db_session.add(self._snapshot(lineup.id, 1))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_two_lineups_can_use_the_same_cap_number(
        self, db_session: AsyncSession
    ):
        first = await self._lineup(db_session)
        second = await self._lineup(db_session)
        db_session.add_all([self._snapshot(first.id, 1), self._snapshot(second.id, 1)])

        await db_session.commit()
