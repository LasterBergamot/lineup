"""Two signed-in users must never see or touch each other's data (OWASP A01 / API1), while the
members of one team share everything that team owns.

Every test runs as user A first, then flips `current_user.id` to user B and tries to reach A's
rows by id. An unknown id and somebody else's id must look identical (404), so the API never
confirms that another user's row exists.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import TeamMember
from tests.conftest import CurrentUser
from tests.helpers import create_player


def _as_other_user(current_user: CurrentUser) -> None:
    current_user.id = uuid.uuid4()


async def _team(client: AsyncClient, name: str = "Alpha", is_public: bool = True):
    r = await client.post("/teams", json={"name": name, "is_public": is_public})
    assert r.status_code == 201
    return r.json()


def _lineup(team_id: str, **overrides) -> dict:
    body = {
        "team_id": team_id,
        "team_name": "Home",
        "opponent_name": "Away",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Coach",
        "players": [{"name": "P", "nssz_number": "N1", "cap_number": 1}],
    }
    body.update(overrides)
    return body


async def _save(client: AsyncClient, team_id: str, **overrides) -> dict:
    r = await client.post("/lineups/saved", json=_lineup(team_id, **overrides))
    assert r.status_code == 201, r.text
    return r.json()


async def _join(db_session: AsyncSession, team_id: str, user_id: uuid.UUID):
    db_session.add(
        TeamMember(team_id=uuid.UUID(team_id), user_id=user_id, role="member")
    )
    await db_session.commit()


class TestTeams:
    async def test_other_users_team_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        _as_other_user(current_user)

        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 404
        assert (
            await async_client.put(f"/teams/{team['id']}", json={"name": "Mine now"})
        ).status_code == 404
        assert (await async_client.delete(f"/teams/{team['id']}")).status_code == 404
        assert (await async_client.get("/teams")).json()["total"] == 0

    async def test_the_creator_is_the_owner(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        assert (await async_client.get(f"/teams/{team['id']}")).status_code == 200
        assert team["created_by"] == str(current_user.id)
        assert team["role"] == "owner"


class TestPlayers:
    async def test_other_users_player_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        player = await create_player(async_client)
        _as_other_user(current_user)

        assert (await async_client.get(f"/players/{player['id']}")).status_code == 404
        body = {"name": "X", "nssz_number": "Y", "team_id": player["team_id"]}
        assert (
            await async_client.put(f"/players/{player['id']}", json=body)
        ).status_code == 404
        assert (
            await async_client.delete(f"/players/{player['id']}")
        ).status_code == 404
        assert (await async_client.get("/players")).json()["total"] == 0
        assert (await async_client.get(f"/players?team_id={player['team_id']}")).json()[
            "total"
        ] == 0

    async def test_cannot_put_a_player_into_someone_elses_team(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        _as_other_user(current_user)
        r = await async_client.post(
            "/players",
            json={"name": "X", "nssz_number": "Y", "team_id": team["id"]},
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Team not found"}

    async def test_cannot_move_a_player_into_someone_elses_team(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        foreign = await _team(async_client, "Foreign")
        _as_other_user(current_user)
        mine = await _team(async_client, "Mine")
        player = await create_player(async_client, team_id=mine["id"])
        r = await async_client.put(
            f"/players/{player['id']}",
            json={"name": "X", "nssz_number": "Y", "team_id": foreign["id"]},
        )
        assert r.status_code == 404
        unchanged = (await async_client.get(f"/players/{player['id']}")).json()
        assert unchanged["team_id"] == mine["id"]

    async def test_teammates_share_the_roster(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        db_session: AsyncSession,
    ):
        team = await _team(async_client)
        player = await create_player(async_client, team_id=team["id"])
        colleague = uuid.uuid4()
        await _join(db_session, team["id"], colleague)

        current_user.id = colleague
        assert (await async_client.get(f"/players/{player['id']}")).status_code == 200
        added = await create_player(
            async_client, "By colleague", "N2", team_id=team["id"]
        )
        assert added["team_id"] == team["id"]
        assert (
            await async_client.delete(f"/players/{player['id']}")
        ).status_code == 204


class TestSavedLineups:
    async def test_other_users_lineup_is_invisible(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        lineup = await _save(async_client, team["id"])
        _as_other_user(current_user)

        assert (
            await async_client.get(f"/lineups/saved/{lineup['id']}")
        ).status_code == 404
        assert (
            await async_client.delete(f"/lineups/saved/{lineup['id']}")
        ).status_code == 404
        generate = await async_client.post(f"/lineups/saved/{lineup['id']}/generate")
        assert generate.status_code == 404
        assert (await async_client.get("/lineups/saved")).json()["total"] == 0
        assert (await async_client.get(f"/lineups/saved?team_id={team['id']}")).json()[
            "total"
        ] == 0

    async def test_teammates_share_saved_lineups(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        db_session: AsyncSession,
    ):
        team = await _team(async_client)
        lineup = await _save(async_client, team["id"])
        colleague = uuid.uuid4()
        await _join(db_session, team["id"], colleague)

        current_user.id = colleague
        assert (
            await async_client.get(f"/lineups/saved/{lineup['id']}")
        ).status_code == 200
        assert (await async_client.get("/lineups/saved")).json()["total"] == 1
        assert (
            await async_client.delete(f"/lineups/saved/{lineup['id']}")
        ).status_code == 204

    async def test_cannot_save_a_lineup_into_someone_elses_team(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        team = await _team(async_client)
        _as_other_user(current_user)
        r = await async_client.post("/lineups/saved", json=_lineup(team["id"]))
        assert r.status_code == 404
        assert r.json() == {"detail": "Team not found"}


class TestSavedLineupCreateCannotReachForeignRows:
    """The IDOR: `source_*_id` values are looked up on behalf of the caller only."""

    async def test_foreign_source_team_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        secret = await _team(async_client, "Secret FC")
        _as_other_user(current_user)
        mine = await _team(async_client, "Mine")
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(mine["id"], team_name=None, source_team_id=secret["id"]),
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Team not found"}
        assert "Secret" not in r.text

    async def test_foreign_source_player_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        player = await create_player(async_client)
        _as_other_user(current_user)
        mine = await _team(async_client, "Mine")
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(
                mine["id"],
                players=[{"source_player_id": player["id"], "cap_number": 1}],
            ),
        )
        assert r.status_code == 404
        assert "Török" not in r.text and "MVLSZ001" not in r.text

    async def test_foreign_private_opponent_is_404(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        private = await _team(async_client, "Private FC", is_public=False)
        _as_other_user(current_user)
        mine = await _team(async_client, "Mine")
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(
                mine["id"], opponent_name=None, source_opponent_id=private["id"]
            ),
        )
        assert r.status_code == 404
        assert r.json() == {"detail": "Opponent team not found"}

    async def test_foreign_listed_opponent_resolves(
        self, async_client: AsyncClient, current_user: CurrentUser
    ):
        listed = await _team(async_client, "Listed FC", is_public=True)
        _as_other_user(current_user)
        mine = await _team(async_client, "Mine")
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(
                mine["id"], opponent_name=None, source_opponent_id=listed["id"]
            ),
        )
        assert r.status_code == 201
        assert r.json()["opponent_name"] == "Listed FC"

    async def test_own_private_opponent_resolves(self, async_client: AsyncClient):
        mine = await _team(async_client, "Mine FC", is_public=False)
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(mine["id"], opponent_name=None, source_opponent_id=mine["id"]),
        )
        assert r.status_code == 201
        assert r.json()["opponent_name"] == "Mine FC"

    async def test_a_teammates_player_can_be_picked(
        self,
        async_client: AsyncClient,
        current_user: CurrentUser,
        db_session: AsyncSession,
    ):
        team = await _team(async_client)
        player = await create_player(async_client, team_id=team["id"])
        colleague = uuid.uuid4()
        await _join(db_session, team["id"], colleague)
        current_user.id = colleague
        r = await async_client.post(
            "/lineups/saved",
            json=_lineup(
                team["id"],
                players=[{"source_player_id": player["id"], "cap_number": 1}],
            ),
        )
        assert r.status_code == 201
        assert r.json()["players"][0]["name"] == "Török András"
