"""Invitation links (#51): create, list, revoke, preview and accept.

Every test that needs a second person flips `current_user.id` (the conftest sign-in override).
Expiry is tested by editing the row, not by sleeping or patching the clock.
"""

import hashlib
import logging
import uuid
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import app
from lineup.auth.dependencies import get_current_display_name, get_current_user_id
from lineup.db.models import TeamInvitation, TeamMember, _utcnow
from lineup.invitations import service
from lineup.security.rate_limit import LIMITERS
from lineup.teams import repository as team_repository
from tests.conftest import CurrentUser
from tests.helpers import ensure_team, join_team


async def _create(client: AsyncClient, team_id: str, **body) -> dict:
    response = await client.post(f"/teams/{team_id}/invitations", json=body or None)
    assert response.status_code == 201, response.text
    return response.json()


async def _expire(db_session: AsyncSession, invitation_id: str, ago: timedelta) -> None:
    await db_session.execute(
        update(TeamInvitation)
        .where(TeamInvitation.id == uuid.UUID(invitation_id))
        .values(expires_at=_utcnow() - ago)
    )
    await db_session.commit()


def _go_anonymous() -> None:
    """Drop the sign-in override: requests now carry no token."""
    app.dependency_overrides.pop(get_current_user_id)


class TestCreate:
    async def test_owner_gets_a_link_valid_for_24_hours_by_default(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        body = await _create(async_client, team["id"])
        assert body["role"] == "member"
        assert body["url"] == f"http://localhost:5173/join/{body['code']}"
        assert len(body["code"]) >= 43  # token_urlsafe(32)
        expires = _utcnow() + timedelta(hours=24)
        assert abs(_expire_delta(body["expires_at"], expires)) < 60

    @pytest.mark.parametrize("hours", [2, 24, 72])
    async def test_expiry_can_be_chosen(self, async_client: AsyncClient, hours: int):
        team = await ensure_team(async_client)
        body = await _create(async_client, team["id"], expires_in_hours=hours)
        expected = _utcnow() + timedelta(hours=hours)
        assert abs(_expire_delta(body["expires_at"], expected)) < 60

    async def test_other_lifetimes_are_rejected(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/invitations", json={"expires_in_hours": 5}
        )
        assert response.status_code == 422

    async def test_url_uses_app_base_url(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("APP_BASE_URL", "https://lineup-kfi.pages.dev/")
        team = await ensure_team(async_client)
        body = await _create(async_client, team["id"])
        assert body["url"] == f"https://lineup-kfi.pages.dev/join/{body['code']}"

    async def test_only_the_hash_of_the_code_is_stored(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        body = await _create(async_client, team["id"])
        row = (await db_session.execute(select(TeamInvitation))).scalar_one()
        assert row.invite_code_hash == hashlib.sha256(body["code"].encode()).hexdigest()
        stored = [str(getattr(row, c.key)) for c in TeamInvitation.__table__.columns]
        assert not any(body["code"] in value for value in stored)

    async def test_every_link_has_its_own_code(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        first = await _create(async_client, team["id"])
        second = await _create(async_client, team["id"])
        assert first["code"] != second["code"]

    async def test_members_cannot_invite(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        current_user.id = uuid.uuid4()
        await join_team(db_session, team["id"], current_user.id)
        response = await async_client.post(f"/teams/{team['id']}/invitations")
        assert response.status_code == 403

    async def test_strangers_and_unknown_teams_get_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        current_user.id = uuid.uuid4()
        stranger = await async_client.post(f"/teams/{team['id']}/invitations")
        unknown = await async_client.post(f"/teams/{uuid.uuid4()}/invitations")
        assert stranger.status_code == unknown.status_code == 404
        assert stranger.json() == unknown.json()

    async def test_creation_is_rate_limited_per_user(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        team = await ensure_team(async_client)
        monkeypatch.setattr(LIMITERS["invite:user"], "limit", 2)
        await _create(async_client, team["id"])
        await _create(async_client, team["id"])
        response = await async_client.post(f"/teams/{team['id']}/invitations")
        assert response.status_code == 429
        assert "Retry-After" in response.headers


def _expire_delta(iso: str, expected) -> float:
    from datetime import datetime

    return (datetime.fromisoformat(iso) - expected).total_seconds()


class TestList:
    async def test_lists_working_links_without_codes(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        created = await _create(async_client, team["id"])
        response = await async_client.get(f"/teams/{team['id']}/invitations")
        assert response.status_code == 200
        [item] = response.json()
        assert item["id"] == created["id"]
        assert set(item) == {"id", "role", "created_at", "expires_at"}
        assert created["code"] not in response.text

    async def test_revoked_and_expired_links_are_not_listed(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        keep = await _create(async_client, team["id"])
        revoked = await _create(async_client, team["id"])
        expired = await _create(async_client, team["id"])
        await async_client.delete(f"/teams/{team['id']}/invitations/{revoked['id']}")
        await _expire(db_session, expired["id"], timedelta(minutes=1))
        response = await async_client.get(f"/teams/{team['id']}/invitations")
        assert [i["id"] for i in response.json()] == [keep["id"]]

    async def test_newest_first(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        first = await _create(async_client, team["id"])
        second = await _create(async_client, team["id"])
        response = await async_client.get(f"/teams/{team['id']}/invitations")
        assert [i["id"] for i in response.json()] == [second["id"], first["id"]]

    async def test_links_a_week_past_expiry_are_deleted(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        old = await _create(async_client, team["id"])
        recent = await _create(async_client, team["id"])
        await _expire(db_session, old["id"], timedelta(days=8))
        await _expire(db_session, recent["id"], timedelta(days=1))
        await async_client.get(f"/teams/{team['id']}/invitations")
        ids = (await db_session.execute(select(TeamInvitation.id))).scalars().all()
        assert [str(i) for i in ids] == [recent["id"]]

    async def test_creating_a_link_also_purges(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        old = await _create(async_client, team["id"])
        await _expire(db_session, old["id"], timedelta(days=8))
        new = await _create(async_client, team["id"])
        ids = (await db_session.execute(select(TeamInvitation.id))).scalars().all()
        assert [str(i) for i in ids] == [new["id"]]

    async def test_members_cannot_list_and_strangers_get_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        url = f"/teams/{team['id']}/invitations"
        current_user.id = uuid.uuid4()
        assert (await async_client.get(url)).status_code == 404
        await join_team(db_session, team["id"], current_user.id)
        assert (await async_client.get(url)).status_code == 403


class TestRevoke:
    async def test_revoked_link_stops_working(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        response = await async_client.delete(
            f"/teams/{team['id']}/invitations/{link['id']}"
        )
        assert response.status_code == 204
        assert (
            await async_client.get(f"/invitations/{link['code']}")
        ).status_code == 410
        accept = await async_client.post(f"/invitations/{link['code']}/accept")
        assert accept.status_code == 410

    async def test_revoking_twice_is_fine(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        url = f"/teams/{team['id']}/invitations/{link['id']}"
        assert (await async_client.delete(url)).status_code == 204
        first = (
            await db_session.execute(select(TeamInvitation.revoked_at))
        ).scalar_one()
        assert (await async_client.delete(url)).status_code == 204
        await db_session.rollback()
        second = (
            await db_session.execute(select(TeamInvitation.revoked_at))
        ).scalar_one()
        assert first == second

    async def test_people_who_already_joined_stay(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        owner = current_user.id
        current_user.id = uuid.uuid4()
        assert (
            await async_client.post(f"/invitations/{link['code']}/accept")
        ).status_code == 200
        current_user.id = owner
        await async_client.delete(f"/teams/{team['id']}/invitations/{link['id']}")
        members = (await async_client.get(f"/teams/{team['id']}/members")).json()
        assert len(members) == 2

    async def test_an_invitation_of_another_team_is_404(
        self, async_client: AsyncClient
    ):
        mine = await ensure_team(async_client, "Mine")
        other = await ensure_team(async_client, "Other")
        link = await _create(async_client, other["id"])
        response = await async_client.delete(
            f"/teams/{mine['id']}/invitations/{link['id']}"
        )
        assert response.status_code == 404
        # ... and it was not revoked by the attempt
        assert (
            await async_client.get(f"/invitations/{link['code']}")
        ).status_code == 200

    async def test_unknown_invitation_is_404(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.delete(
            f"/teams/{team['id']}/invitations/{uuid.uuid4()}"
        )
        assert response.status_code == 404

    async def test_members_cannot_revoke(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        current_user.id = uuid.uuid4()
        url = f"/teams/{team['id']}/invitations/{link['id']}"
        assert (await async_client.delete(url)).status_code == 404
        await join_team(db_session, team["id"], current_user.id)
        assert (await async_client.delete(url)).status_code == 403


class TestPreview:
    async def test_needs_no_sign_in_and_reveals_little(self, async_client: AsyncClient):
        app.dependency_overrides[get_current_display_name] = lambda: "Török András"
        team = await ensure_team(async_client, "Ferencváros")
        link = await _create(async_client, team["id"])
        _go_anonymous()
        response = await async_client.get(f"/invitations/{link['code']}")
        assert response.status_code == 200
        assert response.json() == {
            "team_name": "Ferencváros",
            "invited_by_name": "Török András",
            "expires_at": link["expires_at"],
        }

    async def test_inviter_name_may_be_unknown(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        response = await async_client.get(f"/invitations/{link['code']}")
        assert response.json()["invited_by_name"] is None

    async def test_unknown_code_is_404(self, async_client: AsyncClient):
        response = await async_client.get("/invitations/not-a-real-code")
        assert response.status_code == 404

    async def test_expired_link_is_410(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        await _expire(db_session, link["id"], timedelta(seconds=1))
        response = await async_client.get(f"/invitations/{link['code']}")
        assert response.status_code == 410

    async def test_overlong_code_is_rejected(self, async_client: AsyncClient):
        assert (await async_client.get(f"/invitations/{'a' * 201}")).status_code == 422

    async def test_is_rate_limited_per_ip(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(LIMITERS["invite:ip"], "limit", 2)
        await async_client.get("/invitations/x")
        await async_client.get("/invitations/x")
        response = await async_client.get("/invitations/x")
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestAccept:
    async def test_joining_makes_you_a_member_who_shares_the_roster(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        current_user.id = uuid.uuid4()
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 200
        assert response.json()["id"] == team["id"]
        assert response.json()["role"] == "member"
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200

    async def test_accepting_twice_changes_nothing(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        current_user.id = uuid.uuid4()
        first = await async_client.post(f"/invitations/{link['code']}/accept")
        second = await async_client.post(f"/invitations/{link['code']}/accept")
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()

    async def test_an_owner_opening_the_link_stays_owner(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 200
        assert response.json()["role"] == "owner"

    async def test_one_link_admits_many_people(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        for _ in range(3):
            current_user.id = uuid.uuid4()
            response = await async_client.post(f"/invitations/{link['code']}/accept")
            assert response.status_code == 200

    @pytest.mark.parametrize("how", ["expired", "revoked"])
    async def test_dead_links_are_410(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
        how: str,
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        if how == "expired":
            await _expire(db_session, link["id"], timedelta(seconds=1))
        else:
            await async_client.delete(f"/teams/{team['id']}/invitations/{link['id']}")
        current_user.id = uuid.uuid4()
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 410
        members = (
            await db_session.execute(
                select(TeamMember).where(TeamMember.user_id == current_user.id)
            )
        ).all()
        assert members == []

    async def test_unknown_code_is_404(self, async_client: AsyncClient):
        response = await async_client.post("/invitations/not-a-real-code/accept")
        assert response.status_code == 404

    async def test_needs_sign_in(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        _go_anonymous()
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 401

    async def test_is_rate_limited_per_user_and_per_ip(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(LIMITERS["invite:user"], "limit", 1)
        await async_client.post("/invitations/x/accept")
        response = await async_client.post("/invitations/x/accept")
        assert response.status_code == 429
        monkeypatch.setattr(LIMITERS["invite:user"], "limit", 10)
        monkeypatch.setattr(LIMITERS["invite:ip"], "limit", 1)
        current_user.id = uuid.uuid4()
        assert (await async_client.post("/invitations/x/accept")).status_code == 429

    async def test_losing_the_double_click_race_is_still_a_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        current_user.id = uuid.uuid4()
        await join_team(db_session, team["id"], current_user.id)
        db_session.expunge_all()  # this request's session has not seen the row yet
        real = team_repository.get_membership
        calls = []

        async def first_call_misses(*args, **kwargs):
            calls.append(1)
            return None if len(calls) == 1 else await real(*args, **kwargs)

        monkeypatch.setattr(team_repository, "get_membership", first_call_misses)
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 200
        assert response.json()["role"] == "member"

    async def test_a_team_deleted_mid_accept_is_404(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        monkeypatch: pytest.MonkeyPatch,
    ):
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        current_user.id = uuid.uuid4()

        async def nothing(*args, **kwargs):
            return None

        monkeypatch.setattr(team_repository, "add_member", nothing)
        response = await async_client.post(f"/invitations/{link['code']}/accept")
        assert response.status_code == 404


class TestSecrets:
    async def test_codes_and_names_never_reach_the_logs(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        caplog: pytest.LogCaptureFixture,
    ):
        caplog.set_level(logging.DEBUG)
        app.dependency_overrides[get_current_display_name] = lambda: "Secret Sámuel"
        team = await ensure_team(async_client)
        link = await _create(async_client, team["id"])
        await async_client.get(f"/invitations/{link['code']}")
        current_user.id = uuid.uuid4()
        await async_client.post(f"/invitations/{link['code']}/accept")
        await async_client.post("/invitations/some-bad-code/accept")
        # Only the API's own loggers count: httpx (the test client) logs the URLs it requests and
        # SQLAlchemy/aiosqlite log bound parameters at DEBUG, neither of which runs in production.
        server_logs = "\n".join(
            r.getMessage()
            for r in caplog.records
            if r.name.startswith(("lineup", "uvicorn", "fastapi", "starlette"))
        )
        assert link["code"] not in server_logs
        assert "Secret Sámuel" not in server_logs


class TestAppBaseUrl:
    def test_defaults_to_the_vite_dev_server(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("APP_BASE_URL", raising=False)
        assert service.app_base_url() == "http://localhost:5173"

    def test_blank_means_unset_and_trailing_slash_is_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("APP_BASE_URL", "  ")
        assert service.app_base_url() == "http://localhost:5173"
        monkeypatch.setenv("APP_BASE_URL", "https://example.test/")
        assert service.app_base_url() == "https://example.test"
