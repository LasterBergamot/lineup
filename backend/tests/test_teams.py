"""
Tests for GET/POST /teams, GET/PUT/DELETE /teams/{id}, and GET /teams/pool.
Each test gets a fresh in-memory SQLite DB via the async_client fixture.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import TeamMember
from lineup.teams.schemas import TeamPoolItem
from lineup.teams import repository as team_repo
from tests.conftest import CurrentUser
from tests.helpers import create_player


async def _create_team(
    async_client: AsyncClient, name: str = "SZVTK", is_public: bool = True
) -> dict:
    response = await async_client.post(
        "/teams", json={"name": name, "is_public": is_public}
    )
    assert response.status_code == 201
    return response.json()


async def _create_player(
    async_client: AsyncClient,
    name: str = "Török András",
    nssz_number: str = "MVLSZ001",
    team_id: str | None = None,
) -> dict:
    return await create_player(async_client, name, nssz_number, team_id)


async def _join(db_session: AsyncSession, team_id: str, user_id: uuid.UUID, role: str):
    """Make `user_id` a member of the team (there is no invitation endpoint yet)."""
    db_session.add(TeamMember(team_id=uuid.UUID(team_id), user_id=user_id, role=role))
    await db_session.commit()


class TestCreateTeam:
    async def test_create_team_returns_201(self, async_client: AsyncClient):
        response = await async_client.post("/teams", json={"name": "SZVTK"})
        assert response.status_code == 201

    async def test_create_team_returns_correct_name(self, async_client: AsyncClient):
        response = await async_client.post("/teams", json={"name": "Csongrád"})
        assert response.json()["name"] == "Csongrád"

    async def test_create_team_returns_id(self, async_client: AsyncClient):
        response = await async_client.post("/teams", json={"name": "SZVTK"})
        assert "id" in response.json()

    async def test_create_team_defaults_is_public_true(self, async_client: AsyncClient):
        response = await async_client.post("/teams", json={"name": "SZVTK"})
        assert response.json()["is_public"] is True

    async def test_create_team_is_public_false(self, async_client: AsyncClient):
        response = await async_client.post(
            "/teams", json={"name": "SZVTK", "is_public": False}
        )
        assert response.json()["is_public"] is False

    async def test_creator_becomes_the_owner_member(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await _create_team(async_client)
        members = (await db_session.execute(select(TeamMember))).scalars().all()
        assert [(str(m.team_id), m.user_id, m.role) for m in members] == [
            (team["id"], current_user.id, "owner")
        ]

    async def test_create_team_empty_name_returns_422(self, async_client: AsyncClient):
        response = await async_client.post("/teams", json={"name": ""})
        assert response.status_code == 422

    async def test_create_team_missing_name_returns_422(
        self, async_client: AsyncClient
    ):
        response = await async_client.post("/teams", json={})
        assert response.status_code == 422


class TestListTeams:
    async def test_list_teams_empty(self, async_client: AsyncClient):
        response = await async_client.get("/teams")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_teams_returns_created_team(self, async_client: AsyncClient):
        await _create_team(async_client, "SZVTK")
        response = await async_client.get("/teams")
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["name"] == "SZVTK"

    async def test_list_teams_pagination_limit(self, async_client: AsyncClient):
        for i in range(5):
            await _create_team(async_client, f"Team {i}")
        response = await async_client.get("/teams?limit=3")
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3

    async def test_list_teams_pagination_offset(self, async_client: AsyncClient):
        for i in range(5):
            await _create_team(async_client, f"Team {i}")
        response = await async_client.get("/teams?limit=2&offset=3")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 3

    @pytest.mark.parametrize("limit", [0, -1, 201])
    async def test_list_teams_rejects_out_of_range_limit(
        self, async_client: AsyncClient, limit: int
    ):
        response = await async_client.get(f"/teams?limit={limit}")
        assert response.status_code == 422

    async def test_list_teams_accepts_the_maximum_limit(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/teams?limit=200")
        assert response.status_code == 200
        assert response.json()["limit"] == 200


class TestGetTeam:
    async def test_get_team_returns_200(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        response = await async_client.get(f"/teams/{team['id']}")
        assert response.status_code == 200

    async def test_get_team_returns_correct_data(self, async_client: AsyncClient):
        team = await _create_team(async_client, "SZVTK")
        response = await async_client.get(f"/teams/{team['id']}")
        assert response.json()["name"] == "SZVTK"

    async def test_get_team_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.get("/teams/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestUpdateTeam:
    async def test_update_team_returns_updated_name(self, async_client: AsyncClient):
        team = await _create_team(async_client, "Old Name")
        response = await async_client.put(
            f"/teams/{team['id']}", json={"name": "New Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_update_team_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.put(
            "/teams/00000000-0000-0000-0000-000000000000", json={"name": "X"}
        )
        assert response.status_code == 404

    async def test_update_team_unlists_and_relists_it(self, async_client: AsyncClient):
        team = await _create_team(async_client, "Club", is_public=True)
        response = await async_client.put(
            f"/teams/{team['id']}", json={"name": "Club", "is_public": False}
        )
        assert response.json()["is_public"] is False
        assert (await async_client.get("/teams/pool")).json() == []
        response = await async_client.put(
            f"/teams/{team['id']}", json={"name": "Club", "is_public": True}
        )
        assert response.json()["is_public"] is True
        assert len((await async_client.get("/teams/pool")).json()) == 1

    async def test_update_team_without_is_public_leaves_the_listing_alone(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client, "Club", is_public=False)
        response = await async_client.put(f"/teams/{team['id']}", json={"name": "New"})
        assert response.json()["is_public"] is False

    async def test_a_plain_member_cannot_update_the_team(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await _create_team(async_client, "Club")
        member = uuid.uuid4()
        await _join(db_session, team["id"], member, "member")
        current_user.id = member
        response = await async_client.put(
            f"/teams/{team['id']}", json={"name": "Hijack"}
        )
        assert response.status_code == 403
        assert (await async_client.get(f"/teams/{team['id']}")).json()["name"] == "Club"

    async def test_update_team_empty_name_returns_422(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        response = await async_client.put(f"/teams/{team['id']}", json={"name": ""})
        assert response.status_code == 422


class TestDeleteTeam:
    async def test_delete_team_returns_200(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        response = await async_client.delete(f"/teams/{team['id']}")
        assert response.status_code == 200

    async def test_delete_team_response_has_deleted_true(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.delete(f"/teams/{team['id']}")
        assert response.json()["deleted"] is True

    async def test_delete_team_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.delete(
            "/teams/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_delete_team_removes_it_from_list(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        await async_client.delete(f"/teams/{team['id']}")
        response = await async_client.get("/teams")
        assert response.json()["total"] == 0

    async def test_delete_team_blocked_when_team_has_players(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        await _create_player(async_client, team_id=team["id"])
        response = await async_client.delete(f"/teams/{team['id']}")
        assert response.status_code == 409

    async def test_delete_team_blocked_when_team_has_saved_lineups(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        await _save_lineup(async_client, team["id"], "Them")
        response = await async_client.delete(f"/teams/{team['id']}")
        assert response.status_code == 409
        assert "saved lineup" in response.json()["detail"]

    async def test_delete_team_blocked_leaves_team_intact(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        await _create_player(async_client, team_id=team["id"])
        await async_client.delete(f"/teams/{team['id']}")
        response = await async_client.get(f"/teams/{team['id']}")
        assert response.status_code == 200


class TestMembership:
    async def test_response_carries_the_callers_role(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await _create_team(async_client, "Club")
        assert team["role"] == "owner"
        assert team["created_by"] == str(current_user.id)
        member = uuid.uuid4()
        await _join(db_session, team["id"], member, "member")
        current_user.id = member
        as_member = (await async_client.get(f"/teams/{team['id']}")).json()
        assert as_member["role"] == "member"
        listed = (await async_client.get("/teams")).json()["items"]
        assert [(t["name"], t["role"]) for t in listed] == [("Club", "member")]

    async def test_a_member_sees_the_teams_roster_but_a_stranger_does_not(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await _create_team(async_client, "Club")
        await _create_player(async_client, team_id=team["id"])
        colleague = uuid.uuid4()
        await _join(db_session, team["id"], colleague, "member")

        current_user.id = colleague
        assert (await async_client.get("/players")).json()["total"] == 1
        current_user.id = uuid.uuid4()
        assert (await async_client.get("/players")).json()["total"] == 0

    async def test_a_plain_member_cannot_delete_the_team(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        current_user: CurrentUser,
    ):
        team = await _create_team(async_client, "Club")
        member = uuid.uuid4()
        await _join(db_session, team["id"], member, "member")
        current_user.id = member
        response = await async_client.delete(f"/teams/{team['id']}")
        assert response.status_code == 403
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200


def _lineup_body(team_id: str, opponent: str) -> dict:
    return {
        "team_id": team_id,
        "team_name": "Us",
        "opponent_name": opponent,
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Coach",
        "players": [{"name": "P", "nssz_number": "N1", "cap_number": 1}],
    }


async def _save_lineup(client: AsyncClient, team_id: str, opponent: str) -> None:
    response = await client.post("/lineups/saved", json=_lineup_body(team_id, opponent))
    assert response.status_code == 201


class TestRecentOpponents:
    async def test_empty_for_a_new_team(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        response = await async_client.get(f"/teams/{team['id']}/opponents/recent")
        assert response.status_code == 200
        assert response.json() == []

    async def test_distinct_names_most_recent_first(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        for opponent in ("Alpha", "Beta", "Alpha", "Gamma"):
            await _save_lineup(async_client, team["id"], opponent)
        response = await async_client.get(f"/teams/{team['id']}/opponents/recent")
        assert response.json() == ["Gamma", "Alpha", "Beta"]

    async def test_respects_limit(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        for opponent in ("A", "B", "C"):
            await _save_lineup(async_client, team["id"], opponent)
        response = await async_client.get(
            f"/teams/{team['id']}/opponents/recent?limit=2"
        )
        assert len(response.json()) == 2

    @pytest.mark.parametrize("limit", [0, 51])
    async def test_rejects_out_of_range_limit(self, async_client: AsyncClient, limit):
        team = await _create_team(async_client)
        response = await async_client.get(
            f"/teams/{team['id']}/opponents/recent?limit={limit}"
        )
        assert response.status_code == 422

    async def test_only_the_teams_own_lineups_count(self, async_client: AsyncClient):
        mine = await _create_team(async_client, "Mine")
        other = await _create_team(async_client, "Other")
        await _save_lineup(async_client, mine["id"], "Only mine")
        await _save_lineup(async_client, other["id"], "Only other")
        response = await async_client.get(f"/teams/{mine['id']}/opponents/recent")
        assert response.json() == ["Only mine"]

    async def test_non_members_get_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _create_team(async_client)
        await _save_lineup(async_client, team["id"], "Secret opponent")
        current_user.id = uuid.uuid4()
        response = await async_client.get(f"/teams/{team['id']}/opponents/recent")
        assert response.status_code == 404
        assert "Secret" not in response.text


class TestTeamsPool:
    async def test_pool_empty(self, async_client: AsyncClient):
        response = await async_client.get("/teams/pool")
        assert response.status_code == 200
        assert response.json() == []

    async def test_pool_returns_public_team(self, async_client: AsyncClient):
        await _create_team(async_client, "SZVTK", is_public=True)
        response = await async_client.get("/teams/pool")
        names = [t["name"] for t in response.json()]
        assert names == ["SZVTK"]

    async def test_pool_items_expose_only_id_and_name(self, async_client: AsyncClient):
        """Listing a team must never reveal more than its name (no roster, members, owner).
        Adding a field to the pool schema has to fail here first."""
        await _create_team(async_client, "SZVTK", is_public=True)
        [item] = (await async_client.get("/teams/pool")).json()
        assert set(item) == {"id", "name"}
        assert set(TeamPoolItem.model_fields) == {"id", "name"}

    async def test_pool_lists_other_users_public_teams(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        await _create_team(async_client, "Rival FC", is_public=True)
        await _create_team(async_client, "Hidden FC", is_public=False)
        current_user.id = uuid.uuid4()
        names = [t["name"] for t in (await async_client.get("/teams/pool")).json()]
        assert names == ["Rival FC"]

    async def test_pool_excludes_private_team(self, async_client: AsyncClient):
        await _create_team(async_client, "Private Team", is_public=False)
        response = await async_client.get("/teams/pool")
        assert response.json() == []

    async def test_pool_filters_by_search(self, async_client: AsyncClient):
        await _create_team(async_client, "Csongrád VVSE")
        await _create_team(async_client, "SZVTK")
        response = await async_client.get("/teams/pool?search=csong")
        names = [t["name"] for t in response.json()]
        assert names == ["Csongrád VVSE"]

    async def test_pool_search_treats_percent_as_a_literal(
        self, async_client: AsyncClient
    ):
        for name in ("100% Club", "Alpha", "Beta"):
            await _create_team(async_client, name)
        response = await async_client.get("/teams/pool?search=%25")
        assert [t["name"] for t in response.json()] == ["100% Club"]

    async def test_pool_search_treats_underscore_as_a_literal(
        self, async_client: AsyncClient
    ):
        for name in ("A_B", "AxB"):
            await _create_team(async_client, name)
        response = await async_client.get("/teams/pool?search=A_B")
        assert [t["name"] for t in response.json()] == ["A_B"]

    async def test_pool_search_rejects_overlong_term(self, async_client: AsyncClient):
        response = await async_client.get(f"/teams/pool?search={'a' * 121}")
        assert response.status_code == 422

    async def test_pool_respects_limit(self, async_client: AsyncClient):
        for i in range(5):
            await _create_team(async_client, f"Team {i}")
        response = await async_client.get("/teams/pool?limit=2")
        assert len(response.json()) == 2


class TestTeamRepositoryMembership:
    """Membership scoping is exercised directly at the repository layer with real user ids
    that are, and are not, in the team."""

    async def test_get_team_only_for_members(self, db_session: AsyncSession):
        owner, other = uuid.uuid4(), uuid.uuid4()
        team = await team_repo.create_team(
            db_session, name="Owned", created_by=owner, is_public=True
        )
        found = await team_repo.get_team(db_session, team_id=team.id, user_id=owner)
        assert found is not None and found[1] == "owner"
        assert (
            await team_repo.get_team(db_session, team_id=team.id, user_id=other) is None
        )

    async def test_list_teams_only_shows_my_teams(self, db_session: AsyncSession):
        owner = uuid.uuid4()
        await team_repo.create_team(
            db_session, name="Owned", created_by=owner, is_public=True
        )
        await team_repo.create_team(
            db_session, name="Other", created_by=uuid.uuid4(), is_public=True
        )
        items, total = await team_repo.list_teams(db_session, user_id=owner)
        assert total == 1
        assert items[0][0].name == "Owned"

    async def test_an_opponent_must_be_mine_or_listed(self, db_session: AsyncSession):
        me, stranger = uuid.uuid4(), uuid.uuid4()
        private_own = await team_repo.create_team(
            db_session, name="Mine", created_by=me, is_public=False
        )
        private_foreign = await team_repo.create_team(
            db_session, name="Theirs", created_by=stranger, is_public=False
        )
        listed_foreign = await team_repo.create_team(
            db_session, name="Listed", created_by=stranger, is_public=True
        )
        visible = team_repo.get_team_visible
        assert await visible(db_session, team_id=private_own.id, user_id=me)
        assert await visible(db_session, team_id=listed_foreign.id, user_id=me)
        assert await visible(db_session, team_id=private_foreign.id, user_id=me) is None
