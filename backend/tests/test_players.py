"""
Tests for GET/POST /players and GET/PUT/DELETE /players/{id}.
"""

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import Player, Team, TeamMember
from lineup.players import repository as player_repo
from lineup.teams import repository as team_repo
from tests.helpers import create_player


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
    return await create_player(async_client, name, nssz_number, team_id)


def _lineup_payload(team_id: str, player_id: str, cap_number: int = 1) -> dict:
    return {
        "team_id": team_id,
        "team_name": "SZVTK",
        "opponent_name": "Csongrád VVSE",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 01. 01.",
        "coach": "Coach",
        "players": [{"source_player_id": player_id, "cap_number": cap_number}],
    }


class TestCreatePlayer:
    async def test_create_player_returns_201(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/players",
            json={
                "name": "Test Player",
                "nssz_number": "MVLSZ001",
                "team_id": team["id"],
            },
        )
        assert response.status_code == 201

    async def test_create_player_returns_correct_fields(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/players",
            json={
                "name": "Test Player",
                "nssz_number": "MVLSZ001",
                "team_id": team["id"],
            },
        )
        data = response.json()
        assert data["name"] == "Test Player"
        assert data["nssz_number"] == "MVLSZ001"
        assert data["team_id"] == team["id"]
        assert "id" in data

    async def test_create_player_requires_a_team(self, async_client: AsyncClient):
        response = await async_client.post(
            "/players", json={"name": "Test Player", "nssz_number": "MVLSZ001"}
        )
        assert response.status_code == 422

    async def test_create_player_empty_name_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/players",
            json={"name": "", "nssz_number": "MVLSZ001", "team_id": team["id"]},
        )
        assert response.status_code == 422

    async def test_create_player_missing_nssz_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/players", json={"name": "Player", "team_id": team["id"]}
        )
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

    @pytest.mark.parametrize("limit", [0, -1, 201])
    async def test_list_players_rejects_out_of_range_limit(
        self, async_client: AsyncClient, limit: int
    ):
        response = await async_client.get(f"/players?limit={limit}")
        assert response.status_code == 422

    async def test_list_players_accepts_the_maximum_limit(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/players?limit=200")
        assert response.status_code == 200

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
            json={
                "name": "New Name",
                "nssz_number": "NEW001",
                "team_id": player["team_id"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["nssz_number"] == "NEW001"

    async def test_update_player_moves_to_another_of_my_teams(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client, "Second team")
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

    async def test_update_player_to_an_unknown_team_returns_404(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        response = await async_client.put(
            f"/players/{player['id']}",
            json={
                "name": "X",
                "nssz_number": "Y",
                "team_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert response.status_code == 404

    async def test_update_player_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.put(
            "/players/00000000-0000-0000-0000-000000000000",
            json={
                "name": "X",
                "nssz_number": "Y",
                "team_id": "00000000-0000-0000-0000-000000000000",
            },
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
                "/lineups/saved",
                json=_lineup_payload(player["team_id"], player["id"]),
            )
        ).json()

        response = await async_client.delete(f"/players/{player['id']}")
        assert response.status_code == 204

        get_response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert get_response.json()["players"][0]["name"] == "Locked Player"
        assert get_response.json()["players"][0]["nssz_number"] == "LOCK001"


DUPLICATE_DETAIL = "A player with this NSSZ number is already on this team"


def _body(team_id: str, name: str = "Név", nssz_number: str = "MVLSZ-1") -> dict:
    return {"name": name, "nssz_number": nssz_number, "team_id": team_id}


class TestDuplicateNssz:
    """#284: one NSSZ number once per team (case-insensitive), 409 with a generic body."""

    async def test_create_with_a_number_already_on_the_roster_returns_409(
        self, async_client: AsyncClient
    ):
        first = await _create_player(async_client, "Első", "MVLSZ-1")
        response = await async_client.post(
            "/players", json=_body(first["team_id"], "Másik", "MVLSZ-1")
        )
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE_DETAIL}

    async def test_the_409_does_not_describe_the_other_player(
        self, async_client: AsyncClient
    ):
        first = await _create_player(async_client, "Egyedi Név", "SECRET-42")
        response = await async_client.post(
            "/players", json=_body(first["team_id"], "Másik", "secret-42")
        )
        assert response.status_code == 409
        for leaked in ("Egyedi Név", "SECRET-42", first["id"]):
            assert leaked not in response.text

    async def test_the_comparison_ignores_case_and_surrounding_spaces(
        self, async_client: AsyncClient
    ):
        first = await _create_player(async_client, "Első", "mvlsz-abc")
        response = await async_client.post(
            "/players", json=_body(first["team_id"], "Másik", "  MVLSZ-ABC ")
        )
        assert response.status_code == 409

    async def test_the_same_number_in_another_team_is_allowed(
        self, async_client: AsyncClient
    ):
        first = await _create_player(async_client, "Első", "MVLSZ-1")
        other = await _create_team(async_client, "Másik csapat")
        response = await async_client.post(
            "/players", json=_body(other["id"], "Első", "MVLSZ-1")
        )
        assert response.status_code == 201
        assert response.json()["team_id"] != first["team_id"]

    async def test_the_same_name_with_a_new_number_is_allowed(
        self, async_client: AsyncClient
    ):
        first = await _create_player(async_client, "Kovács Béla", "MVLSZ-1")
        response = await async_client.post(
            "/players", json=_body(first["team_id"], "Kovács Béla", "MVLSZ-2")
        )
        assert response.status_code == 201

    async def test_update_to_a_number_on_the_roster_returns_409(
        self, async_client: AsyncClient
    ):
        await _create_player(async_client, "Első", "MVLSZ-1")
        second = await _create_player(async_client, "Második", "MVLSZ-2")
        response = await async_client.put(
            f"/players/{second['id']}",
            json=_body(second["team_id"], "Második", "mvlsz-1"),
        )
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE_DETAIL}
        # unchanged
        stored = await async_client.get(f"/players/{second['id']}")
        assert stored.json()["nssz_number"] == "MVLSZ-2"

    async def test_update_keeping_the_own_number_is_allowed(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client, "Régi", "MVLSZ-1")
        response = await async_client.put(
            f"/players/{player['id']}", json=_body(player["team_id"], "Új", "MVLSZ-1")
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Új"

    async def test_moving_a_player_to_a_team_that_has_the_number_returns_409(
        self, async_client: AsyncClient
    ):
        mine = await _create_player(async_client, "Első", "MVLSZ-1")
        other = await _create_team(async_client, "Másik csapat")
        await _create_player(async_client, "Őt is", "MVLSZ-1", team_id=other["id"])
        response = await async_client.put(
            f"/players/{mine['id']}", json=_body(other["id"], "Első", "MVLSZ-1")
        )
        assert response.status_code == 409

    async def test_a_deleted_players_number_can_be_added_again(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client, "Első", "MVLSZ-1")
        await async_client.delete(f"/players/{player['id']}")
        response = await async_client.post(
            "/players", json=_body(player["team_id"], "Első", "MVLSZ-1")
        )
        assert response.status_code == 201

    async def test_two_concurrent_creates_with_the_same_number_one_wins(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        responses = await asyncio.gather(
            *(
                async_client.post("/players", json=_body(team["id"], f"P{i}", "RACE-1"))
                for i in range(2)
            )
        )
        assert sorted(r.status_code for r in responses) == [201, 409]

    async def test_a_create_that_loses_the_race_after_the_check_is_a_409(
        self, async_client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        """The pre-check passes (nobody there yet), then another request inserts the number
        before this one commits: the unique index refuses and the answer is the same 409."""
        team = await _create_team(async_client)
        real = player_repo.nssz_taken
        calls = []

        async def blind_first_time(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                db_session.add(
                    Player(
                        name="Gyorsabb",
                        nssz_number="RACE-2",
                        team_id=uuid.UUID(team["id"]),
                        created_by=uuid.uuid4(),
                    )
                )
                await db_session.commit()
                return False
            return await real(*args, **kwargs)

        monkeypatch.setattr(player_repo, "nssz_taken", blind_first_time)
        response = await async_client.post(
            "/players", json=_body(team["id"], "Lassabb", "race-2")
        )
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE_DETAIL}
        assert len(calls) == 2
        db_session.expire_all()
        rows = (await db_session.execute(select(Player))).scalars().all()
        assert [p.name for p in rows] == ["Gyorsabb"]

    async def test_an_update_that_loses_the_race_after_the_check_is_a_409(
        self, async_client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        mine = await _create_player(async_client, "Enyém", "MVLSZ-1")
        real = player_repo.nssz_taken
        calls = []

        async def blind_first_time(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                db_session.add(
                    Player(
                        name="Gyorsabb",
                        nssz_number="RACE-3",
                        team_id=uuid.UUID(mine["team_id"]),
                        created_by=uuid.uuid4(),
                    )
                )
                await db_session.commit()
                return False
            return await real(*args, **kwargs)

        monkeypatch.setattr(player_repo, "nssz_taken", blind_first_time)
        response = await async_client.put(
            f"/players/{mine['id']}", json=_body(mine["team_id"], "Enyém", "RACE-3")
        )
        assert response.status_code == 409
        assert response.json() == {"detail": DUPLICATE_DETAIL}

    async def test_an_integrity_error_with_another_cause_is_not_called_a_duplicate(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Only the NSSZ index is reported as the duplicate; anything else keeps the app-wide
        generic 409 (`handle_integrity_error`), not this endpoint's sentence."""
        team = await _create_team(async_client)

        async def boom(*args, **kwargs):
            raise IntegrityError("INSERT", {}, Exception("other"))

        monkeypatch.setattr(player_repo, "create_player", boom)
        response = await async_client.post("/players", json=_body(team["id"]))
        assert response.status_code == 409
        assert response.json() == {"detail": "The request conflicts with existing data"}

    async def test_an_update_integrity_error_with_another_cause_is_not_called_a_duplicate(
        self, async_client: AsyncClient, monkeypatch
    ):
        player = await _create_player(async_client)

        async def boom(*args, **kwargs):
            raise IntegrityError("UPDATE", {}, Exception("other"))

        monkeypatch.setattr(player_repo, "update_player", boom)
        response = await async_client.put(
            f"/players/{player['id']}", json=_body(player["team_id"], "X", "Y")
        )
        assert response.status_code == 409
        assert response.json() == {"detail": "The request conflicts with existing data"}

    async def test_no_log_line_contains_the_number(
        self, async_client: AsyncClient, caplog
    ):
        first = await _create_player(async_client, "Első", "LOGGED-NSSZ-9")
        with caplog.at_level("DEBUG", logger="lineup"):
            await async_client.post(
                "/players", json=_body(first["team_id"], "Második", "LOGGED-NSSZ-9")
            )
        ours = [r.getMessage() for r in caplog.records if r.name.startswith("lineup")]
        assert not any("LOGGED-NSSZ-9" in message for message in ours)


class TestNsszUniqueIndex:
    """The database refuses what the service would, so no code path can slip past (#284)."""

    async def test_the_index_rejects_a_case_variant_in_the_same_team(
        self, db_session: AsyncSession
    ):
        user = uuid.uuid4()
        team = await team_repo.create_team(
            db_session, name="T", created_by=user, is_public=True
        )
        await player_repo.create_player(
            db_session, name="A", nssz_number="abc1", created_by=user, team_id=team.id
        )
        with pytest.raises(IntegrityError):
            await player_repo.create_player(
                db_session,
                name="B",
                nssz_number="ABC1",
                created_by=user,
                team_id=team.id,
            )

    async def test_the_index_allows_the_number_in_another_team(
        self, db_session: AsyncSession
    ):
        user = uuid.uuid4()
        one = await team_repo.create_team(
            db_session, name="T1", created_by=user, is_public=True
        )
        two = await team_repo.create_team(
            db_session, name="T2", created_by=user, is_public=True
        )
        for team in (one, two):
            await player_repo.create_player(
                db_session, name="A", nssz_number="N1", created_by=user, team_id=team.id
            )


class TestPlayerRepositoryMembership:
    """Membership scoping is exercised directly at the repository layer so that the
    functions are checked with real user ids that are, and are not, in the team."""

    async def _team(self, db_session: AsyncSession, member: uuid.UUID) -> Team:
        return await team_repo.create_team(
            db_session, name="T", created_by=member, is_public=True
        )

    async def test_get_player_only_for_team_members(self, db_session: AsyncSession):
        user, other = uuid.uuid4(), uuid.uuid4()
        team = await self._team(db_session, user)
        player = await player_repo.create_player(
            db_session, name="P", nssz_number="N1", created_by=user, team_id=team.id
        )
        assert (
            await player_repo.get_player(db_session, player_id=player.id, user_id=user)
            is not None
        )
        assert (
            await player_repo.get_player(db_session, player_id=player.id, user_id=other)
            is None
        )

    async def test_a_member_who_did_not_create_the_player_can_use_it(
        self, db_session: AsyncSession
    ):
        creator, colleague = uuid.uuid4(), uuid.uuid4()
        team = await self._team(db_session, creator)
        db_session.add(TeamMember(team_id=team.id, user_id=colleague, role="member"))
        await db_session.commit()
        player = await player_repo.create_player(
            db_session,
            name="P",
            nssz_number="N1",
            created_by=creator,
            team_id=team.id,
        )
        found = await player_repo.get_player(
            db_session, player_id=player.id, user_id=colleague
        )
        assert found is not None and found.created_by == creator

    async def test_list_players_only_shows_my_teams(self, db_session: AsyncSession):
        user, other = uuid.uuid4(), uuid.uuid4()
        mine, theirs = (
            await self._team(db_session, user),
            await self._team(db_session, other),
        )
        await player_repo.create_player(
            db_session, name="P1", nssz_number="N1", created_by=user, team_id=mine.id
        )
        await player_repo.create_player(
            db_session, name="P2", nssz_number="N2", created_by=other, team_id=theirs.id
        )
        items, total = await player_repo.list_players(db_session, user_id=user)
        assert total == 1
        assert items[0].name == "P1"
        # filtering by somebody else's team gives nothing, not their players
        items, total = await player_repo.list_players(
            db_session, user_id=user, team_id=theirs.id
        )
        assert (items, total) == ([], 0)
