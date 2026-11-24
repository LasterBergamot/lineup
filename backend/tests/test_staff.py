"""Tests for `/teams/{team_id}/staff`: the coach, assistant coach, team leader and ball thrower
a team keeps. Covers CRUD for members, the 404 rules (non-member, foreign staff id, foreign
`source_player_id`), the one-default-per-role rule, and what deleting a player or a team does."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import TeamStaff
from lineup.staff import repository as staff_repo
from tests.conftest import CurrentUser
from tests.helpers import create_player, ensure_team, join_team


def _body(**overrides) -> dict:
    body = {"role": "coach", "name": "Kiss Béla"}
    body.update(overrides)
    return body


async def _add(client: AsyncClient, team_id: str, **overrides) -> dict:
    response = await client.post(f"/teams/{team_id}/staff", json=_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


async def _count(db_session: AsyncSession) -> int:
    db_session.expire_all()
    return await db_session.scalar(select(func.count()).select_from(TeamStaff))


class TestCrud:
    async def test_create_returns_the_entry(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/staff",
            json=_body(role="assistant_coach", name="  Nagy Pál  "),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["team_id"] == team["id"]
        assert body["role"] == "assistant_coach"
        assert body["name"] == "Nagy Pál"
        assert body["source_player_id"] is None
        assert body["is_default"] is False
        assert body["created_at"]
        assert set(body) == {
            "id",
            "team_id",
            "role",
            "name",
            "source_player_id",
            "is_default",
            "created_at",
        }

    async def test_list_returns_all_roles_in_creation_order(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        first = await _add(async_client, team["id"], role="coach", name="A")
        second = await _add(async_client, team["id"], role="coach", name="B")
        third = await _add(async_client, team["id"], role="ball_thrower", name="C")
        response = await async_client.get(f"/teams/{team['id']}/staff")
        assert response.status_code == 200
        assert [s["id"] for s in response.json()] == [
            first["id"],
            second["id"],
            third["id"],
        ]

    async def test_list_of_a_team_without_staff_is_empty(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        response = await async_client.get(f"/teams/{team['id']}/staff")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_only_shows_this_teams_staff(self, async_client: AsyncClient):
        mine = await ensure_team(async_client, "Mine")
        other = await ensure_team(async_client, "Other")
        await _add(async_client, mine["id"], name="Mine")
        await _add(async_client, other["id"], name="Other")
        listed = (await async_client.get(f"/teams/{mine['id']}/staff")).json()
        assert [s["name"] for s in listed] == ["Mine"]

    async def test_a_role_can_have_several_entries(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        await _add(async_client, team["id"], name="A")
        await _add(async_client, team["id"], name="A")
        assert len((await async_client.get(f"/teams/{team['id']}/staff")).json()) == 2

    async def test_update_replaces_every_field(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        player = await create_player(async_client, "Szabó Gábor", team_id=team["id"])
        staff = await _add(async_client, team["id"])
        response = await async_client.put(
            f"/teams/{team['id']}/staff/{staff['id']}",
            json=_body(
                role="team_leader",
                name="Szabó Gábor",
                source_player_id=player["id"],
                is_default=True,
            ),
        )
        assert response.status_code == 200
        assert response.json() == {
            **staff,
            "role": "team_leader",
            "name": "Szabó Gábor",
            "source_player_id": player["id"],
            "is_default": True,
        }

    async def test_update_without_the_optional_fields_clears_them(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        player = await create_player(async_client, team_id=team["id"])
        staff = await _add(
            async_client,
            team["id"],
            source_player_id=player["id"],
            is_default=True,
        )
        response = await async_client.put(
            f"/teams/{team['id']}/staff/{staff['id']}", json=_body(name="Új Név")
        )
        assert response.status_code == 200
        assert response.json()["source_player_id"] is None
        assert response.json()["is_default"] is False
        assert response.json()["name"] == "Új Név"

    async def test_delete_returns_204_and_removes_it(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team = await ensure_team(async_client)
        staff = await _add(async_client, team["id"])
        response = await async_client.delete(f"/teams/{team['id']}/staff/{staff['id']}")
        assert response.status_code == 204
        assert await _count(db_session) == 0
        assert (await async_client.get(f"/teams/{team['id']}/staff")).json() == []

    async def test_deleting_a_default_promotes_nobody(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        await _add(async_client, team["id"], name="Other")
        default = await _add(async_client, team["id"], name="Boss", is_default=True)
        await async_client.delete(f"/teams/{team['id']}/staff/{default['id']}")
        listed = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert [(s["name"], s["is_default"]) for s in listed] == [("Other", False)]

    async def test_created_by_is_the_caller(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        await _add(async_client, team["id"])
        row = (await db_session.execute(select(TeamStaff))).scalar_one()
        assert row.created_by == current_user.id


class TestValidation:
    @pytest.mark.parametrize(
        "bad",
        [
            {"name": ""},
            {"name": "   "},
            {"name": "x" * 201},
            {"name": "Tab\there"},
            {"role": "doctor"},
            {"role": "Coach"},
            {"role": ""},
            {"is_default": "maybe"},
            {"source_player_id": "not-a-uuid"},
        ],
    )
    async def test_bad_bodies_are_422(self, async_client: AsyncClient, bad: dict):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/staff", json=_body(**bad)
        )
        assert response.status_code == 422

    async def test_missing_fields_are_422(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        for body in ({}, {"role": "coach"}, {"name": "X"}):
            response = await async_client.post(f"/teams/{team['id']}/staff", json=body)
            assert response.status_code == 422

    async def test_a_body_with_contact_fields_does_not_store_them(
        self, async_client: AsyncClient
    ):
        """G4: names only. Unknown fields are ignored and never returned."""
        team = await ensure_team(async_client)
        staff = await _add(
            async_client, team["id"], phone="+36 1 234", email="a@example.com"
        )
        assert "phone" not in staff and "email" not in staff

    async def test_a_malformed_ids_are_422(self, async_client: AsyncClient):
        assert (await async_client.get("/teams/nope/staff")).status_code == 422
        team = await ensure_team(async_client)
        response = await async_client.put(
            f"/teams/{team['id']}/staff/nope", json=_body()
        )
        assert response.status_code == 422


class TestDefaults:
    async def test_a_new_default_replaces_the_old_one_of_the_same_role(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        old = await _add(async_client, team["id"], name="Old", is_default=True)
        new = await _add(async_client, team["id"], name="New", is_default=True)
        assert new["is_default"] is True
        listed = {
            s["id"]: s["is_default"]
            for s in (await async_client.get(f"/teams/{team['id']}/staff")).json()
        }
        assert listed == {old["id"]: False, new["id"]: True}

    async def test_each_role_has_its_own_default(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        await _add(async_client, team["id"], role="coach", is_default=True)
        await _add(async_client, team["id"], role="assistant_coach", is_default=True)
        await _add(async_client, team["id"], role="team_leader", is_default=True)
        await _add(async_client, team["id"], role="ball_thrower", is_default=True)
        listed = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert [s["is_default"] for s in listed] == [True] * 4

    async def test_each_team_has_its_own_default(self, async_client: AsyncClient):
        one = await ensure_team(async_client, "One")
        two = await ensure_team(async_client, "Two")
        a = await _add(async_client, one["id"], is_default=True)
        b = await _add(async_client, two["id"], is_default=True)
        assert a["is_default"] and b["is_default"]
        listed = (await async_client.get(f"/teams/{one['id']}/staff")).json()
        assert listed[0]["is_default"] is True

    async def test_making_an_entry_the_default_on_update_clears_the_other(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        old = await _add(async_client, team["id"], name="Old", is_default=True)
        new = await _add(async_client, team["id"], name="New")
        response = await async_client.put(
            f"/teams/{team['id']}/staff/{new['id']}",
            json=_body(name="New", is_default=True),
        )
        assert response.status_code == 200
        listed = {
            s["id"]: s["is_default"]
            for s in (await async_client.get(f"/teams/{team['id']}/staff")).json()
        }
        assert listed == {old["id"]: False, new["id"]: True}

    async def test_saving_the_current_default_again_keeps_it(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        staff = await _add(async_client, team["id"], name="Boss", is_default=True)
        response = await async_client.put(
            f"/teams/{team['id']}/staff/{staff['id']}",
            json=_body(name="Boss Renamed", is_default=True),
        )
        assert response.status_code == 200
        assert response.json()["is_default"] is True

    async def test_moving_a_default_into_a_role_replaces_that_roles_default(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        leader = await _add(
            async_client, team["id"], role="team_leader", name="L", is_default=True
        )
        coach = await _add(
            async_client, team["id"], role="coach", name="C", is_default=True
        )
        response = await async_client.put(
            f"/teams/{team['id']}/staff/{coach['id']}",
            json=_body(role="team_leader", name="C", is_default=True),
        )
        assert response.status_code == 200
        listed = {
            s["id"]: (s["role"], s["is_default"])
            for s in (await async_client.get(f"/teams/{team['id']}/staff")).json()
        }
        assert listed == {
            leader["id"]: ("team_leader", False),
            coach["id"]: ("team_leader", True),
        }

    async def test_unsetting_the_default_leaves_the_role_without_one(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        staff = await _add(async_client, team["id"], is_default=True)
        await async_client.put(
            f"/teams/{team['id']}/staff/{staff['id']}", json=_body(is_default=False)
        )
        listed = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert [s["is_default"] for s in listed] == [False]

    async def test_a_lost_race_is_a_409_not_two_defaults(
        self, async_client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        """If another request sets a default between our clear and our commit, the partial
        unique index refuses the second one and the app-wide handler answers 409."""
        team = await ensure_team(async_client)
        await _add(async_client, team["id"], name="First", is_default=True)

        async def no_clear(*_args, **_kwargs):
            """Pretend the clearing UPDATE saw nothing: that is what a lost race looks like."""

        monkeypatch.setattr(staff_repo, "_clear_default", no_clear)
        response = await async_client.post(
            f"/teams/{team['id']}/staff", json=_body(name="Second", is_default=True)
        )
        assert response.status_code == 409
        assert "Second" not in response.text
        db_session.expire_all()
        rows = (await db_session.execute(select(TeamStaff))).scalars().all()
        assert [r.name for r in rows] == ["First"]


class TestSourcePlayer:
    async def test_picking_from_the_roster_records_the_link(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        player = await create_player(async_client, "Horváth Ede", team_id=team["id"])
        staff = await _add(
            async_client, team["id"], name="Horváth Ede", source_player_id=player["id"]
        )
        assert staff["source_player_id"] == player["id"]

    async def test_a_name_that_differs_from_the_player_is_kept_as_sent(
        self, async_client: AsyncClient
    ):
        """The name is a copy chosen by the client, not looked up from the player."""
        team = await ensure_team(async_client)
        player = await create_player(async_client, "Horváth Ede", team_id=team["id"])
        staff = await _add(
            async_client, team["id"], name="Ede bácsi", source_player_id=player["id"]
        )
        assert staff["name"] == "Ede bácsi"

    async def test_an_unknown_player_is_404(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.post(
            f"/teams/{team['id']}/staff",
            json=_body(source_player_id=str(uuid.uuid4())),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Player not found"

    async def test_a_player_of_another_team_is_404_even_if_you_are_in_both(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        one = await ensure_team(async_client, "One")
        two = await ensure_team(async_client, "Two")
        elsewhere = await create_player(async_client, team_id=two["id"])
        response = await async_client.post(
            f"/teams/{one['id']}/staff", json=_body(source_player_id=elsewhere["id"])
        )
        assert response.status_code == 404
        assert await _count(db_session) == 0

    async def test_a_player_of_a_team_you_are_not_in_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        mine = await ensure_team(async_client, "Mine")
        owner = current_user.id
        current_user.id = uuid.uuid4()
        stranger_team = await ensure_team(async_client, "Stranger")
        stranger_player = await create_player(
            async_client, "Secret Person", "S1", stranger_team["id"]
        )
        current_user.id = owner
        response = await async_client.post(
            f"/teams/{mine['id']}/staff",
            json=_body(source_player_id=stranger_player["id"]),
        )
        assert response.status_code == 404
        assert "Secret" not in response.text

    async def test_update_with_a_foreign_player_is_404_and_changes_nothing(
        self, async_client: AsyncClient
    ):
        one = await ensure_team(async_client, "One")
        two = await ensure_team(async_client, "Two")
        elsewhere = await create_player(async_client, team_id=two["id"])
        staff = await _add(async_client, one["id"], name="Stays")
        response = await async_client.put(
            f"/teams/{one['id']}/staff/{staff['id']}",
            json=_body(name="Changed", source_player_id=elsewhere["id"]),
        )
        assert response.status_code == 404
        listed = (await async_client.get(f"/teams/{one['id']}/staff")).json()
        assert [s["name"] for s in listed] == ["Stays"]

    async def test_deleting_the_player_keeps_the_name_and_nulls_the_link(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        player = await create_player(async_client, "Horváth Ede", team_id=team["id"])
        await _add(
            async_client,
            team["id"],
            name="Horváth Ede",
            source_player_id=player["id"],
            is_default=True,
        )
        assert (
            await async_client.delete(f"/players/{player['id']}")
        ).status_code == 204
        (staff,) = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert staff["name"] == "Horváth Ede"
        assert staff["source_player_id"] is None
        assert staff["is_default"] is True

    async def test_renaming_the_player_does_not_touch_the_staff_name(
        self, async_client: AsyncClient
    ):
        team = await ensure_team(async_client)
        player = await create_player(async_client, "Old Name", team_id=team["id"])
        await _add(
            async_client, team["id"], name="Old Name", source_player_id=player["id"]
        )
        await async_client.put(
            f"/players/{player['id']}",
            json={"name": "New Name", "nssz_number": "MVLSZ001", "team_id": team["id"]},
        )
        (staff,) = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert staff["name"] == "Old Name"


class TestTeamDeletion:
    async def test_deleting_a_team_removes_its_staff_only(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        gone = await ensure_team(async_client, "Gone")
        kept = await ensure_team(async_client, "Kept")
        await _add(async_client, gone["id"], name="Goes", is_default=True)
        await _add(async_client, kept["id"], name="Stays")
        assert (await async_client.delete(f"/teams/{gone['id']}")).status_code == 200
        db_session.expire_all()
        names = (await db_session.execute(select(TeamStaff.name))).scalars().all()
        assert names == ["Stays"]

    async def test_staff_does_not_block_deleting_a_team(
        self, async_client: AsyncClient
    ):
        """The 409 rule is about players and saved lineups only."""
        team = await ensure_team(async_client)
        await _add(async_client, team["id"])
        assert (await async_client.delete(f"/teams/{team['id']}")).status_code == 200


class TestAccess:
    """A team is a workspace: any member may use its staff, nobody else may see it exist."""

    async def test_a_plain_member_can_do_everything(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        staff = await _add(async_client, team["id"], name="By owner")
        member = uuid.uuid4()
        await join_team(db_session, team["id"], member)
        current_user.id = member

        listed = (await async_client.get(f"/teams/{team['id']}/staff")).json()
        assert [s["name"] for s in listed] == ["By owner"]
        created = await _add(async_client, team["id"], name="By member")
        put = await async_client.put(
            f"/teams/{team['id']}/staff/{staff['id']}", json=_body(name="Edited")
        )
        assert put.status_code == 200
        delete = await async_client.delete(f"/teams/{team['id']}/staff/{created['id']}")
        assert delete.status_code == 204

    async def test_a_non_member_gets_404_on_everything(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await ensure_team(async_client)
        staff = await _add(async_client, team["id"], name="Private Person")
        current_user.id = uuid.uuid4()
        base = f"/teams/{team['id']}/staff"

        responses = [
            await async_client.get(base),
            await async_client.post(base, json=_body()),
            await async_client.put(f"{base}/{staff['id']}", json=_body(name="Hax")),
            await async_client.delete(f"{base}/{staff['id']}"),
        ]
        assert [r.status_code for r in responses] == [404] * 4
        assert all("Private" not in r.text for r in responses)
        db_session.expire_all()
        row = (await db_session.execute(select(TeamStaff))).scalar_one()
        assert row.name == "Private Person"

    async def test_an_unknown_team_looks_the_same(self, async_client: AsyncClient):
        base = f"/teams/{uuid.uuid4()}/staff"
        assert (await async_client.get(base)).status_code == 404
        assert (await async_client.post(base, json=_body())).status_code == 404

    async def test_a_staff_id_of_another_team_is_404(self, async_client: AsyncClient):
        """Both teams are yours, but the staff id must belong to the team in the path."""
        one = await ensure_team(async_client, "One")
        two = await ensure_team(async_client, "Two")
        staff = await _add(async_client, two["id"], name="Two's")
        put = await async_client.put(
            f"/teams/{one['id']}/staff/{staff['id']}", json=_body(name="Moved")
        )
        delete = await async_client.delete(f"/teams/{one['id']}/staff/{staff['id']}")
        assert (put.status_code, delete.status_code) == (404, 404)
        assert put.json()["detail"] == "Staff member not found"
        listed = (await async_client.get(f"/teams/{two['id']}/staff")).json()
        assert [s["name"] for s in listed] == ["Two's"]

    async def test_an_unknown_staff_id_is_404(self, async_client: AsyncClient):
        team = await ensure_team(async_client)
        response = await async_client.delete(
            f"/teams/{team['id']}/staff/{uuid.uuid4()}"
        )
        assert response.status_code == 404

    async def test_nothing_is_logged_with_a_name(
        self, async_client: AsyncClient, caplog
    ):
        team = await ensure_team(async_client)
        # Only the app's own loggers: SQLAlchemy/driver debug output would echo bound values.
        with caplog.at_level("DEBUG", logger="lineup"):
            staff = await _add(async_client, team["id"], name="Logged Name")
            await async_client.put(
                f"/teams/{team['id']}/staff/{staff['id']}",
                json=_body(name="Logged Name 2"),
            )
            await async_client.delete(f"/teams/{team['id']}/staff/{staff['id']}")
        app_logs = [
            r.getMessage() for r in caplog.records if r.name.startswith("lineup")
        ]
        assert not any("Logged Name" in message for message in app_logs)


class TestDatabaseGuards:
    """The constraints themselves, below the service."""

    async def _team_id(self, async_client: AsyncClient) -> uuid.UUID:
        return uuid.UUID((await ensure_team(async_client))["id"])

    def _row(self, team_id, **kwargs) -> TeamStaff:
        values = {
            "team_id": team_id,
            "role": "coach",
            "name": "N",
            "created_by": uuid.uuid4(),
        }
        values.update(kwargs)
        return TeamStaff(**values)

    async def test_a_second_default_for_a_role_is_refused_by_the_index(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team_id = await self._team_id(async_client)
        db_session.add(self._row(team_id, is_default=True))
        await db_session.commit()
        db_session.add(self._row(team_id, is_default=True))
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_many_non_defaults_and_defaults_of_other_roles_are_fine(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team_id = await self._team_id(async_client)
        db_session.add_all(
            [
                self._row(team_id),
                self._row(team_id),
                self._row(team_id, is_default=True),
                self._row(team_id, role="team_leader", is_default=True),
            ]
        )
        await db_session.commit()
        assert await _count(db_session) == 4

    async def test_an_unknown_role_is_refused_by_the_check_constraint(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        team_id = await self._team_id(async_client)
        db_session.add(self._row(team_id, role="doctor"))
        with pytest.raises(IntegrityError):
            await db_session.commit()
