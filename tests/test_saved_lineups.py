"""
Tests for GET/POST /lineups/saved and GET/DELETE /lineups/saved/{id}.
Also covers the snapshot/soft-reference design: lineups freeze team/opponent/
player data as text at creation time, so deleting the source team or player
afterwards has zero effect on a previously saved lineup.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot
from lineup.saved_lineups import repository as saved_lineup_repo

FAKE_PDF = b"%PDF-1.4 fake"


async def _create_team(async_client: AsyncClient, name: str = "SZVTK") -> dict:
    r = await async_client.post("/teams", json={"name": name})
    assert r.status_code == 201
    return r.json()


async def _create_player(
    async_client: AsyncClient,
    name: str = "Török András",
    nssz_number: str = "MVLSZ001",
) -> dict:
    r = await async_client.post(
        "/players", json={"name": name, "nssz_number": nssz_number}
    )
    assert r.status_code == 201
    return r.json()


def _lineup_payload(
    source_team_id: str, source_player_id: str, cap_number: int = 1
) -> dict:
    return {
        "source_team_id": source_team_id,
        "opponent_name": "Csongrád VVSE",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Török András",
        "doctor": "Török András",
        "assistant_coach": "Török András",
        "team_leader": "Török András",
        "ball_thrower": "Török András",
        "players": [{"source_player_id": source_player_id, "cap_number": cap_number}],
    }


class TestCreateSavedLineup:
    async def test_create_lineup_returns_201(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        response = await async_client.post(
            "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
        )
        assert response.status_code == 201

    async def test_create_lineup_returns_correct_data(self, async_client: AsyncClient):
        team = await _create_team(async_client, "SZVTK")
        player = await _create_player(async_client, "Török András", "MVLSZ001")
        response = await async_client.post(
            "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
        )
        data = response.json()
        assert data["source_team_id"] == team["id"]
        assert data["team_name"] == "SZVTK"
        assert data["opponent_name"] == "Csongrád VVSE"
        assert data["match_name"] == "SZVTK - Csongrád VVSE"
        assert len(data["players"]) == 1
        assert data["players"][0]["name"] == "Török András"
        assert data["players"][0]["nssz_number"] == "MVLSZ001"
        assert data["players"][0]["cap_number"] == 1
        assert data["players"][0]["source_player_id"] == player["id"]

    async def test_create_lineup_with_free_text_team_and_opponent(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/lineups/saved",
            json={
                "team_name": "Home Club",
                "opponent_name": "Away Club",
                "division": "OB II.",
                "cap": "Fehér",
                "date": "2024. 12. 21.",
                "coach": "Coach",
                "players": [
                    {"name": "Free Player", "nssz_number": "FREE001", "cap_number": 1}
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["team_name"] == "Home Club"
        assert data["opponent_name"] == "Away Club"
        assert data["source_team_id"] is None
        assert data["source_opponent_id"] is None
        assert data["match_name"] == "Home Club - Away Club"
        assert data["players"][0]["name"] == "Free Player"
        assert data["players"][0]["source_player_id"] is None

    async def test_create_lineup_custom_match_name_overrides_derived(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client, "SZVTK")
        player = await _create_player(async_client)
        payload = _lineup_payload(team["id"], player["id"])
        payload["match_name"] = "Custom Match Name"
        response = await async_client.post("/lineups/saved", json=payload)
        assert response.json()["match_name"] == "Custom Match Name"

    async def test_create_lineup_nonexistent_source_team_returns_404(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json=_lineup_payload("00000000-0000-0000-0000-000000000000", player["id"]),
        )
        assert response.status_code == 404

    async def test_create_lineup_nonexistent_source_player_returns_404(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json=_lineup_payload(team["id"], "00000000-0000-0000-0000-000000000000"),
        )
        assert response.status_code == 404

    async def test_create_lineup_missing_team_identity_returns_422(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json={
                "opponent_name": "Csongrád VVSE",
                "division": "OB II.",
                "cap": "Fehér",
                "date": "2024. 12. 21.",
                "coach": "Coach",
                "players": [{"source_player_id": player["id"], "cap_number": 1}],
            },
        )
        assert response.status_code == 422

    async def test_create_lineup_missing_opponent_identity_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json={
                "source_team_id": team["id"],
                "division": "OB II.",
                "cap": "Fehér",
                "date": "2024. 12. 21.",
                "coach": "Coach",
                "players": [{"source_player_id": player["id"], "cap_number": 1}],
            },
        )
        assert response.status_code == 422

    async def test_create_lineup_player_missing_identity_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json={
                "source_team_id": team["id"],
                "opponent_name": "Csongrád VVSE",
                "division": "OB II.",
                "cap": "Fehér",
                "date": "2024. 12. 21.",
                "coach": "Coach",
                "players": [{"cap_number": 1}],
            },
        )
        assert response.status_code == 422

    async def test_create_lineup_duplicate_cap_numbers_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        p1 = await _create_player(async_client, "Player A", "MVLSZ001")
        p2 = await _create_player(async_client, "Player B", "MVLSZ002")
        response = await async_client.post(
            "/lineups/saved",
            json={
                **_lineup_payload(team["id"], p1["id"]),
                "players": [
                    {"source_player_id": p1["id"], "cap_number": 1},
                    {"source_player_id": p2["id"], "cap_number": 1},  # duplicate
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_lineup_duplicate_source_player_ids_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json={
                **_lineup_payload(team["id"], player["id"]),
                "players": [
                    {"source_player_id": player["id"], "cap_number": 1},
                    {"source_player_id": player["id"], "cap_number": 2},
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_lineup_invalid_cap_returns_422(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        payload = _lineup_payload(team["id"], player["id"])
        payload["cap"] = "Piros"
        response = await async_client.post("/lineups/saved", json=payload)
        assert response.status_code == 422


class TestListSavedLineups:
    async def test_list_lineups_empty(self, async_client: AsyncClient):
        response = await async_client.get("/lineups/saved")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_lineups_returns_created_lineup(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        await async_client.post(
            "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
        )
        response = await async_client.get("/lineups/saved")
        assert response.json()["total"] == 1

    async def test_list_lineups_filter_by_source_team_id(
        self, async_client: AsyncClient
    ):
        team1 = await _create_team(async_client, "Team 1")
        team2 = await _create_team(async_client, "Team 2")
        player = await _create_player(async_client)
        await async_client.post(
            "/lineups/saved", json=_lineup_payload(team1["id"], player["id"])
        )
        await async_client.post(
            "/lineups/saved", json=_lineup_payload(team2["id"], player["id"])
        )
        response = await async_client.get(
            f"/lineups/saved?source_team_id={team1['id']}"
        )
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source_team_id"] == team1["id"]

    async def test_list_lineups_pagination(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        for _ in range(5):
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        response = await async_client.get("/lineups/saved?limit=3")
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5

    async def test_list_lineups_limit_zero_returns_all(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        for _ in range(5):
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        response = await async_client.get("/lineups/saved?limit=0")
        assert len(response.json()["items"]) == 5


class TestGetSavedLineup:
    async def test_get_lineup_returns_200(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        created = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        response = await async_client.get(f"/lineups/saved/{created['id']}")
        assert response.status_code == 200

    async def test_get_lineup_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.get(
            "/lineups/saved/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestDataIndependence:
    """Saved lineups are frozen snapshots: deleting their source team or
    source player afterwards must never affect the previously saved data."""

    async def test_lineup_survives_team_deletion(self, async_client: AsyncClient):
        team = await _create_team(async_client, "SZVTK")
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()

        delete_response = await async_client.delete(f"/teams/{team['id']}")
        assert delete_response.status_code == 200

        response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert response.status_code == 200
        assert response.json()["team_name"] == "SZVTK"

    async def test_lineup_survives_player_deletion(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client, "Locked Player", "LOCK001")
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()

        delete_response = await async_client.delete(f"/players/{player['id']}")
        assert delete_response.status_code == 204

        response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert response.json()["players"][0]["name"] == "Locked Player"
        assert response.json()["players"][0]["nssz_number"] == "LOCK001"


class TestDeleteSavedLineup:
    async def test_delete_lineup_returns_204(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        response = await async_client.delete(f"/lineups/saved/{lineup['id']}")
        assert response.status_code == 204

    async def test_delete_lineup_not_found_returns_404(self, async_client: AsyncClient):
        response = await async_client.delete(
            "/lineups/saved/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_delete_lineup_removes_from_list(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        await async_client.delete(f"/lineups/saved/{lineup['id']}")
        assert (await async_client.get("/lineups/saved")).json()["total"] == 0


class TestGenerateFromSavedLineup:
    @pytest.fixture(autouse=True)
    def mock_pdf_converter(self):
        with patch(
            "lineup.document.pdf_converter.PdfConverter.convert",
            return_value=FAKE_PDF,
        ):
            yield

    async def test_generate_pdf_from_saved_lineup(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        response = await async_client.post(
            f"/lineups/saved/{lineup['id']}/generate?format=pdf"
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"

    async def test_generate_docx_from_saved_lineup(self, async_client: AsyncClient):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        response = await async_client.post(
            f"/lineups/saved/{lineup['id']}/generate?format=docx"
        )
        assert response.status_code == 200
        assert "wordprocessingml" in response.headers["content-type"]

    async def test_generate_from_nonexistent_lineup_returns_404(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/lineups/saved/00000000-0000-0000-0000-000000000000/generate"
        )
        assert response.status_code == 404

    async def test_generate_uses_team_name_after_team_deleted(
        self, async_client: AsyncClient
    ):
        """Even after the team is deleted, the document should still generate."""
        team = await _create_team(async_client, "SZVTK")
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        await async_client.delete(f"/teams/{team['id']}")
        response = await async_client.post(
            f"/lineups/saved/{lineup['id']}/generate?format=pdf"
        )
        assert response.status_code == 200
        assert "SZVTK" in response.headers["content-disposition"]


class TestSavedLineupRepositoryUserFiltering:
    """User-scoped filtering is exercised directly at the repository layer
    since the auth dependency always yields user_id=None pre-Auth."""

    async def _create(self, db_session: AsyncSession, user_id: uuid.UUID | None):
        snapshot = LineupPlayerSnapshot(
            id=uuid.uuid4(),
            cap_number=1,
            name="P",
            nssz_number="N1",
            source_player_id=None,
        )
        return await saved_lineup_repo.create_saved_lineup(
            db_session,
            team_name="A",
            opponent_name="B",
            match_name="A - B",
            division="OB II.",
            cap="Fehér",
            date="2024. 12. 21.",
            coach="Coach",
            doctor=None,
            assistant_coach=None,
            team_leader=None,
            ball_thrower=None,
            user_id=user_id,
            source_team_id=None,
            source_opponent_id=None,
            player_snapshots=[snapshot],
        )

    async def test_get_saved_lineup_filters_by_user_id(self, db_session: AsyncSession):
        user = uuid.uuid4()
        other = uuid.uuid4()
        lineup = await self._create(db_session, user)
        assert (
            await saved_lineup_repo.get_saved_lineup(
                db_session, lineup_id=lineup.id, user_id=user
            )
            is not None
        )
        assert (
            await saved_lineup_repo.get_saved_lineup(
                db_session, lineup_id=lineup.id, user_id=other
            )
            is None
        )

    async def test_list_saved_lineups_filters_by_user_id(
        self, db_session: AsyncSession
    ):
        user = uuid.uuid4()
        await self._create(db_session, user)
        await self._create(db_session, uuid.uuid4())
        items, total = await saved_lineup_repo.list_saved_lineups(
            db_session, user_id=user
        )
        assert total == 1
