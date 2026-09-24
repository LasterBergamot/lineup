"""
Tests for GET/POST /players and GET/PUT/DELETE /players/{id}.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.players import repository as player_repo


async def _create_team(async_client: AsyncClient, name: str = "SZVTK") -> dict:
    response = await async_client.post("/teams", json={"name": name})
    assert response.status_code == 201
    return response.json()


async def _create_player(
    async_client: AsyncClient,
    name: str = "Török András",
    nssz_number: str = "MVLSZ123456789",
    team_id: str | None = None,
) -> dict:
    payload = {"name": name, "nssz_number": nssz_number}
    if team_id is not None:
        payload["team_id"] = team_id
    response = await async_client.post("/players", json=payload)
    assert response.status_code == 201
    return response.json()


def _lineup_payload(team_name: str, player_id: str, cap_number: int = 1) -> dict:
    return {
        "team_name": team_name,
        "opponent_name": "Csongrád VVSE",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 01. 01.",
        "coach": "Coach",
        "players": [{"source_player_id": player_id, "cap_number": cap_number}],
    }


class TestCreatePlayer:
    async def test_create_player_returns_201(self, async_client: AsyncClient):
        response = await async_client.post(
            "/players", json={"name": "Test Player", "nssz_number": "MVLSZ001"}
        )
        assert response.status_code == 201

    async def test_create_player_returns_correct_fields(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/players", json={"name": "Test Player", "nssz_number": "MVLSZ001"}
        )
        data = response.json()
        assert data["name"] == "Test Player"
        assert data["nssz_number"] == "MVLSZ001"
        assert data["team_id"] is None
        assert "id" in data

    async def test_create_player_with_team_id(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client, team_id=team["id"])
        assert player["team_id"] == team["id"]

    async def test_create_player_empty_name_returns_422(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/players", json={"name": "", "nssz_number": "MVLSZ001"}
        )
        assert response.status_code == 422

    async def test_create_player_missing_nssz_returns_422(
        self, async_client: AsyncClient
    ):
        response = await async_client.post("/players", json={"name": "Player"})
        assert response.status_code == 422


class TestListPlayers:
    async def test_list_players_empty(self, async_client: AsyncClient):
        response = await async_client.get("/players")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_players_returns_created_player(self, async_client: AsyncClient):
        await _create_player(async_client)
        response = await async_client.get("/players")
        assert response.json()["total"] == 1

    async def test_list_players_pagination_limit(self, async_client: AsyncClient):
        for i in range(5):
            await _create_player(async_client, f"Player {i}", f"MVLSZ{i:03d}")
        response = await async_client.get("/players?limit=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_players_limit_zero_returns_all(self, async_client: AsyncClient):
        for i in range(5):
            await _create_player(async_client, f"Player {i}", f"MVLSZ{i:03d}")
        response = await async_client.get("/players?limit=0")
        assert len(response.json()["items"]) == 5

    async def test_list_players_pagination_offset(self, async_client: AsyncClient):
        for i in range(5):
            await _create_player(async_client, f"Player {i}", f"MVLSZ{i:03d}")
        response = await async_client.get("/players?limit=3&offset=2")
        data = response.json()
        assert len(data["items"]) == 3
        assert data["offset"] == 2

    async def test_list_players_filter_by_team_id(self, async_client: AsyncClient):
        team1 = await _create_team(async_client, "Team 1")
        team2 = await _create_team(async_client, "Team 2")
        await _create_player(async_client, "P1", "MVLSZ001", team_id=team1["id"])
        await _create_player(async_client, "P2", "MVLSZ002", team_id=team2["id"])
        response = await async_client.get(f"/players?team_id={team1['id']}")
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "P1"


class TestGetPlayer:
    async def test_get_player_returns_200(self, async_client: AsyncClient):
        player = await _create_player(async_client)
        response = await async_client.get(f"/players/{player['id']}")
        assert response.status_code == 200

    async def test_get_player_returns_correct_data(self, async_client: AsyncClient):
        player = await _create_player(async_client, "Kovács Béla", "MVLSZ999")
        response = await async_client.get(f"/players/{player['id']}")
        data = response.json()
        assert data["name"] == "Kovács Béla"
        assert data["nssz_number"] == "MVLSZ999"

    async def test_get_player_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.get(
            "/players/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestUpdatePlayer:
    async def test_update_player_returns_updated_data(self, async_client: AsyncClient):
        player = await _create_player(async_client, "Old Name", "OLD001")
        response = await async_client.put(
            f"/players/{player['id']}",
            json={"name": "New Name", "nssz_number": "NEW001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["nssz_number"] == "NEW001"

    async def test_update_player_sets_team_id(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        response = await async_client.put(
            f"/players/{player['id']}",
            json={
                "name": player["name"],
                "nssz_number": player["nssz_number"],
                "team_id": team["id"],
            },
        )
        assert response.json()["team_id"] == team["id"]

    async def test_update_player_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.put(
            "/players/00000000-0000-0000-0000-000000000000",
            json={"name": "X", "nssz_number": "Y"},
        )
        assert response.status_code == 404


class TestDeletePlayer:
    async def test_delete_player_returns_204(self, async_client: AsyncClient):
        player = await _create_player(async_client)
        response = await async_client.delete(f"/players/{player['id']}")
        assert response.status_code == 204

    async def test_delete_player_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.delete(
            "/players/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_delete_player_removes_from_list(self, async_client: AsyncClient):
        player = await _create_player(async_client)
        await async_client.delete(f"/players/{player['id']}")
        response = await async_client.get("/players")
        assert response.json()["total"] == 0

    async def test_delete_player_referenced_by_lineup_still_succeeds(
        self, async_client: AsyncClient
    ):
        """Saved lineups are frozen snapshots, so deleting a roster player is
        always safe — it never blocks and never breaks past lineups."""
        player = await _create_player(async_client, "Locked Player", "LOCK001")
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload("SZVTK", player["id"])
            )
        ).json()

        response = await async_client.delete(f"/players/{player['id']}")
        assert response.status_code == 204

        get_response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert get_response.json()["players"][0]["name"] == "Locked Player"
        assert get_response.json()["players"][0]["nssz_number"] == "LOCK001"


class TestPlayerRepositoryUserFiltering:
    """User-scoped filtering is exercised directly at the repository layer
    since the auth dependency always yields user_id=None pre-Auth."""

    async def test_get_player_filters_by_user_id(self, db_session: AsyncSession):
        user = uuid.uuid4()
        other = uuid.uuid4()
        player = await player_repo.create_player(
            db_session, name="P", nssz_number="N1", user_id=user, team_id=None
        )
        assert (
            await player_repo.get_player(db_session, player_id=player.id, user_id=user)
            is not None
        )
        assert (
            await player_repo.get_player(db_session, player_id=player.id, user_id=other)
            is None
        )

    async def test_list_players_filters_by_user_id(self, db_session: AsyncSession):
        user = uuid.uuid4()
        await player_repo.create_player(
            db_session, name="P1", nssz_number="N1", user_id=user, team_id=None
        )
        await player_repo.create_player(
            db_session, name="P2", nssz_number="N2", user_id=uuid.uuid4(), team_id=None
        )
        items, total = await player_repo.list_players(db_session, user_id=user)
        assert total == 1
        assert items[0].name == "P1"
