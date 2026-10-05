"""Two signed-in users must never see or touch each other's data (OWASP A01 / API1).

Every test runs as user A first, then flips `current_user.id` to user B and tries to reach A's
rows by id. An unknown id and somebody else's id must look identical (404), so the API never
confirms that another user's row exists.
"""

import uuid
from httpx import AsyncClient

from tests.conftest import CurrentUser


async def _as_other_user(current_user: CurrentUser) -> None:
    current_user.id = uuid.uuid4()


async def _team(client: AsyncClient, name: str = "Alpha", is_public: bool = True):
    r = await client.post("/teams", json={"name": name, "is_public": is_public})
    assert r.status_code == 201
    return r.json()


async def _player(client: AsyncClient, team_id: str | None = None) -> dict:
    body = {"name": "Török András", "nssz_number": "MVLSZ001", "team_id": team_id}
    r = await client.post("/players", json=body)
    assert r.status_code == 201
    return r.json()


def _lineup(**overrides) -> dict:
    body = {
        "team_name": "Home",
        "opponent_name": "Away",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Coach",
        "players": [{"name": "P", "nssz_number": "N1", "cap_number": 1}],
    }
    return {**body, **overrides}


async def _lineup_as_current_user(client: AsyncClient, **overrides) -> dict:
    r = await client.post("/lineups/saved", json=_lineup(**overrides))
    assert r.status_code == 201
    return r.json()


class TestTeams:
    async def test_other_users_team_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        await _as_other_user(current_user)

        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 404
        assert (
            await async_client.put(f"/teams/{team['id']}", json={"name": "Mine now"})
        ).status_code == 404
        assert (await async_client.delete(f"/teams/{team['id']}")).status_code == 404
        assert (await async_client.get("/teams")).json()["total"] == 0

    async def test_the_owner_still_sees_the_team(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200
        assert team["owner_id"] == str(current_user.id)


class TestPlayers:
    async def test_other_users_player_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        player = await _player(async_client)
        await _as_other_user(current_user)

        assert (await async_client.get(f"/players/{player['id']}")).status_code == 404
        body = {"name": "X", "nssz_number": "Y"}
        assert (
            await async_client.put(f"/players/{player['id']}", json=body)
        ).status_code == 404
        assert (
            await async_client.delete(f"/players/{player['id']}")
        ).status_code == 404
        assert (await async_client.get("/players")).json()["total"] == 0

    async def test_cannot_put_a_player_into_someone_elses_team(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        await _as_other_user(current_user)
        r = await async_client.post(
            "/players",
            json={"name": "X", "nssz_number": "Y", "team_id": team["id"]},
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Team not found"}


class TestSavedLineups:
    async def test_other_users_lineup_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        lineup = await _lineup_as_current_user(async_client)
        await _as_other_user(current_user)

        assert (
            await async_client.get(f"/lineups/saved/{lineup['id']}")
        ).status_code == 404
        assert (
            await async_client.delete(f"/lineups/saved/{lineup['id']}")
        ).status_code == 404
        generate = await async_client.post(f"/lineups/saved/{lineup['id']}/generate")
        assert generate.status_code == 404
        assert (await async_client.get("/lineups/saved")).json()["total"] == 0


class TestSavedLineupCreateCannotReachForeignRows:
    """The IDOR: `source_*_id` values are looked up on behalf of the caller only."""

    async def test_foreign_source_team_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client, "Secret FC")
        await _as_other_user(current_user)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(team_name=None, source_team_id=team["id"]),
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Team not found"}
        assert "Secret" not in r.text

    async def test_foreign_source_player_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        player = await _player(async_client)
        await _as_other_user(current_user)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(players=[{"source_player_id": player["id"], "cap_number": 1}]),
        )
        assert r.status_code == 404
        assert "Török" not in r.text and "MVLSZ001" not in r.text

    async def test_foreign_private_opponent_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client, "Private FC", is_public=False)
        await _as_other_user(current_user)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(opponent_name=None, source_opponent_id=team["id"]),
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Opponent team not found"}

    async def test_foreign_listed_opponent_resolves(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client, "Listed FC", is_public=True)
        await _as_other_user(current_user)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(opponent_name=None, source_opponent_id=team["id"]),
        )
        assert r.status_code == 201
        assert r.json()["opponent_name"] == "Listed FC"

    async def test_own_private_opponent_resolves(self, async_client: AsyncClient):
        team = await _team(async_client, "Mine FC", is_public=False)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(opponent_name=None, source_opponent_id=team["id"]),
        )
        assert r.status_code == 201
        assert r.json()["opponent_name"] == "Mine FC"
