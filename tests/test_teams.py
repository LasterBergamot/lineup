"""
Tests for GET/POST /teams, GET/PUT/DELETE /teams/{id}, and GET /teams/pool.
Each test gets a fresh in-memory SQLite DB via the async_client fixture.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.teams import repository as team_repo


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
    payload = {"name": name, "nssz_number": nssz_number}
    if team_id is not None:
        payload["team_id"] = team_id
    response = await async_client.post("/players", json=payload)
    assert response.status_code == 201
    return response.json()


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

    async def test_list_teams_limit_zero_returns_all(self, async_client: AsyncClient):
        for i in range(5):
            await _create_team(async_client, f"Team {i}")
        response = await async_client.get("/teams?limit=0")
        assert len(response.json()["items"]) == 5


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

    async def test_delete_team_blocked_leaves_team_intact(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        await _create_player(async_client, team_id=team["id"])
        await async_client.delete(f"/teams/{team['id']}")
        response = await async_client.get(f"/teams/{team['id']}")
        assert response.status_code == 200


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

    async def test_pool_respects_limit(self, async_client: AsyncClient):
        for i in range(5):
            await _create_team(async_client, f"Team {i}")
        response = await async_client.get("/teams/pool?limit=2")
        assert len(response.json()) == 2


class TestTeamRepositoryOwnerFiltering:
    """Owner-scoped filtering is exercised directly at the repository layer
    since the auth dependency always yields owner_id=None pre-Auth."""

    async def test_get_team_filters_by_owner_id(self, db_session: AsyncSession):
        owner = uuid.uuid4()
        other = uuid.uuid4()
        team = await team_repo.create_team(
            db_session, name="Owned", owner_id=owner, is_public=True
        )
        assert (
            await team_repo.get_team(db_session, team_id=team.id, owner_id=owner)
            is not None
        )
        assert (
            await team_repo.get_team(db_session, team_id=team.id, owner_id=other)
            is None
        )

    async def test_list_teams_filters_by_owner_id(self, db_session: AsyncSession):
        owner = uuid.uuid4()
        await team_repo.create_team(
            db_session, name="Owned", owner_id=owner, is_public=True
        )
        await team_repo.create_team(
            db_session, name="Other", owner_id=uuid.uuid4(), is_public=True
        )
        items, total = await team_repo.list_teams(db_session, owner_id=owner)
        assert total == 1
        assert items[0].name == "Owned"
