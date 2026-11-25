"""
Tests for GET/POST /lineups/saved and GET/PUT/DELETE /lineups/saved/{id}.
Also covers the snapshot/soft-reference design: lineups copy team/opponent/
player data as text when they are saved or edited, so deleting the source team or player
afterwards has zero effect on a previously saved lineup.
"""

import io
import uuid
import zipfile
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.models import LineupPlayerSnapshot, SavedLineup, TeamMember
from lineup.saved_lineups import repository as saved_lineup_repo
from lineup.saved_lineups import service as saved_lineup_service
from lineup.teams import repository as team_repo
from tests.helpers import create_player, ensure_team, join_team

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
    return await create_player(async_client, name, nssz_number)


def _lineup_payload(
    source_team_id: str, source_player_id: str, cap_number: int = 1
) -> dict:
    return {
        "team_id": source_team_id,
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
                "team_id": (await ensure_team(async_client))["id"],
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
                "team_id": player["team_id"],
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
                "team_id": team["id"],
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
                "team_id": team["id"],
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


class TestMatchDate:
    """`match_date`/`match_time` are stored structured; the server composes the printed text."""

    async def _post(self, async_client: AsyncClient, **changes):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        payload = _lineup_payload(team["id"], player["id"])
        for key, value in changes.items():
            if value is None:
                payload.pop(key, None)
            else:
                payload[key] = value
        return await async_client.post("/lineups/saved", json=payload)

    async def test_free_text_date_stores_no_structured_fields(
        self, async_client: AsyncClient
    ):
        data = (await self._post(async_client)).json()
        assert data["date"] == "2024. 12. 21."
        assert data["match_date"] is None
        assert data["match_time"] is None

    async def test_date_only_is_composed_and_stored(self, async_client: AsyncClient):
        response = await self._post(async_client, date=None, match_date="2026-11-24")
        assert response.status_code == 201
        data = response.json()
        assert data["date"] == "2026. 11. 24."
        assert data["match_date"] == "2026-11-24"
        assert data["match_time"] is None

    async def test_date_and_time_are_composed_and_stored(
        self, async_client: AsyncClient
    ):
        response = await self._post(
            async_client, date=None, match_date="2026-03-05", match_time="08:05"
        )
        data = response.json()
        assert data["date"] == "2026. 03. 05. 08:05"
        assert data["match_time"] == "08:05:00"

    async def test_structured_date_replaces_free_text_and_drops_seconds(
        self, async_client: AsyncClient
    ):
        response = await self._post(
            async_client, match_date="2026-11-24", match_time="18:30:45"
        )
        data = response.json()
        assert data["date"] == "2026. 11. 24. 18:30"
        assert data["match_time"] == "18:30:00"

    async def test_structured_fields_come_back_on_get(self, async_client: AsyncClient):
        created = (
            await self._post(async_client, date=None, match_date="2026-11-24")
        ).json()
        fetched = (await async_client.get(f"/lineups/saved/{created['id']}")).json()
        assert fetched["match_date"] == "2026-11-24"
        assert fetched["date"] == "2026. 11. 24."

    async def test_time_without_date_is_422(self, async_client: AsyncClient):
        response = await self._post(async_client, match_time="18:30")
        assert response.status_code == 422

    async def test_neither_date_nor_match_date_is_422(self, async_client: AsyncClient):
        response = await self._post(async_client, date=None)
        assert response.status_code == 422

    async def test_time_with_timezone_is_422(self, async_client: AsyncClient):
        response = await self._post(
            async_client, match_date="2026-11-24", match_time="18:30+01:00"
        )
        assert response.status_code == 422

    async def test_impossible_date_is_422(self, async_client: AsyncClient):
        response = await self._post(async_client, date=None, match_date="2026-02-30")
        assert response.status_code == 422


class TestLocation:
    async def _save(self, async_client, **extra):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        payload = _lineup_payload(team["id"], player["id"]) | extra
        return await async_client.post("/lineups/saved", json=payload)

    async def test_location_is_stored_and_returned(self, async_client: AsyncClient):
        created = (
            await self._save(async_client, location="  Szeged, Tisza uszoda ")
        ).json()
        assert created["location"] == "Szeged, Tisza uszoda"
        fetched = (await async_client.get(f"/lineups/saved/{created['id']}")).json()
        assert fetched["location"] == "Szeged, Tisza uszoda"
        listed = (await async_client.get("/lineups/saved")).json()
        assert listed["items"][0]["location"] == "Szeged, Tisza uszoda"

    @pytest.mark.parametrize("extra", [{}, {"location": None}, {"location": "   "}])
    async def test_missing_or_blank_location_is_null(
        self, async_client: AsyncClient, extra
    ):
        created = (await self._save(async_client, **extra)).json()
        assert created["location"] is None

    async def test_too_long_location_is_422(self, async_client: AsyncClient):
        response = await self._save(async_client, location="x" * 201)
        assert response.status_code == 422

    async def test_is_home_is_stored_and_returned(self, async_client: AsyncClient):
        for value in (True, False):
            created = (await self._save(async_client, is_home=value)).json()
            assert created["is_home"] is value
            fetched = (await async_client.get(f"/lineups/saved/{created['id']}")).json()
            assert fetched["is_home"] is value
        listed = (await async_client.get("/lineups/saved")).json()
        assert {item["is_home"] for item in listed["items"]} == {True, False}

    @pytest.mark.parametrize("extra", [{}, {"is_home": None}])
    async def test_missing_is_home_is_null(
        self, async_client: AsyncClient, extra: dict
    ):
        created = (await self._save(async_client, **extra)).json()
        assert created["is_home"] is None

    async def test_is_home_does_not_have_to_match_the_cap(
        self, async_client: AsyncClient
    ):
        """A neutral venue: home but in Kék is accepted as sent."""
        created = (await self._save(async_client, is_home=True, cap="Kék")).json()
        assert (created["is_home"], created["cap"]) == (True, "Kék")

    async def test_non_boolean_is_home_is_422(self, async_client: AsyncClient):
        response = await self._save(async_client, is_home="maybe")
        assert response.status_code == 422

    async def test_location_is_not_printed(self, async_client: AsyncClient):
        """The generated DOCX is byte-identical with and without a location."""
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        base = _lineup_payload(team["id"], player["id"])
        plain = (await async_client.post("/lineups/saved", json=base)).json()
        located = (
            await async_client.post(
                "/lineups/saved", json=base | {"location": "Szeged, Tisza uszoda"}
            )
        ).json()
        docs = []
        for lineup in (plain, located):
            response = await async_client.post(
                f"/lineups/saved/{lineup['id']}/generate?format=docx"
            )
            assert response.status_code == 200
            docs.append(response.content)
        assert docs[0] == docs[1]
        assert b"Tisza" not in docs[1]
        with zipfile.ZipFile(io.BytesIO(docs[1])) as z:
            assert b"Tisza" not in z.read("word/document.xml")


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

    @pytest.mark.parametrize("limit", [0, -1, 201])
    async def test_list_lineups_rejects_out_of_range_limit(
        self, async_client: AsyncClient, limit: int
    ):
        response = await async_client.get(f"/lineups/saved?limit={limit}")
        assert response.status_code == 422

    async def test_list_lineups_accepts_the_maximum_limit(
        self, async_client: AsyncClient
    ):
        response = await async_client.get("/lineups/saved?limit=200")
        assert response.status_code == 200


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

    async def test_lineup_survives_source_team_deletion(
        self, async_client: AsyncClient
    ):
        workspace = await ensure_team(async_client, "Workspace")
        source = await _create_team(async_client, "SZVTK")
        player = await create_player(async_client, team_id=workspace["id"])
        payload = {
            **_lineup_payload(source["id"], player["id"]),
            "team_id": workspace["id"],
        }
        lineup = (await async_client.post("/lineups/saved", json=payload)).json()

        delete_response = await async_client.delete(f"/teams/{source['id']}")
        assert delete_response.status_code == 200

        response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert response.status_code == 200
        assert response.json()["team_name"] == "SZVTK"
        assert response.json()["source_team_id"] is None
        assert response.json()["team_id"] == workspace["id"]

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
        assert response.json()["players"][0]["source_player_id"] is None

    async def test_lineup_survives_opponent_deletion(self, async_client: AsyncClient):
        workspace = await ensure_team(async_client, "Workspace")
        opponent = await _create_team(async_client, "Csongrád VVSE")
        player = await create_player(async_client, team_id=workspace["id"])
        payload = _lineup_payload(workspace["id"], player["id"])
        payload.pop("opponent_name")
        payload["source_opponent_id"] = opponent["id"]
        created = await async_client.post("/lineups/saved", json=payload)
        assert created.status_code == 201, created.text
        lineup = created.json()
        assert lineup["source_opponent_id"] == opponent["id"]

        assert (
            await async_client.delete(f"/teams/{opponent['id']}")
        ).status_code == 200

        response = await async_client.get(f"/lineups/saved/{lineup['id']}")
        assert response.json()["opponent_name"] == "Csongrád VVSE"
        assert response.json()["source_opponent_id"] is None


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

    async def test_generate_without_optional_staff_fields(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        payload = _lineup_payload(team["id"], player["id"])
        for staff_field in ("doctor", "assistant_coach", "team_leader", "ball_thrower"):
            del payload[staff_field]
        lineup = (await async_client.post("/lineups/saved", json=payload)).json()
        response = await async_client.post(
            f"/lineups/saved/{lineup['id']}/generate?format=docx"
        )
        assert response.status_code == 200

    async def test_generate_offloads_rendering_to_threadpool(
        self, async_client: AsyncClient
    ):
        """PDF conversion blocks, so it must not run on the event loop."""
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        lineup = (
            await async_client.post(
                "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
            )
        ).json()
        with patch(
            "lineup.api.file_response.run_in_threadpool",
            new=AsyncMock(return_value=FAKE_PDF),
        ) as threadpool:
            response = await async_client.post(
                f"/lineups/saved/{lineup['id']}/generate?format=pdf"
            )
        assert response.status_code == 200
        threadpool.assert_awaited_once()


class TestSavedLineupRepositoryMembership:
    """Membership scoping is exercised directly at the repository layer so that the
    functions are checked with real user ids that are, and are not, in the lineup's team."""

    async def _create(self, db_session: AsyncSession, user_id: uuid.UUID, team_id=None):
        if team_id is None:
            team_id = (
                await team_repo.create_team(
                    db_session, name="T", created_by=user_id, is_public=True
                )
            ).id
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
            match_date=None,
            match_time=None,
            location=None,
            is_home=None,
            coach="Coach",
            doctor=None,
            assistant_coach=None,
            team_leader=None,
            ball_thrower=None,
            created_by=user_id,
            team_id=team_id,
            source_team_id=None,
            source_opponent_id=None,
            player_snapshots=[snapshot],
        )

    async def test_get_saved_lineup_only_for_team_members(
        self, db_session: AsyncSession
    ):
        user, other = uuid.uuid4(), uuid.uuid4()
        lineup = await self._create(db_session, user)
        found = await saved_lineup_repo.get_saved_lineup(
            db_session, lineup_id=lineup.id, user_id=user
        )
        assert found is not None
        assert (
            await saved_lineup_repo.get_saved_lineup(
                db_session, lineup_id=lineup.id, user_id=other
            )
            is None
        )

    async def test_a_colleague_sees_lineups_they_did_not_create(
        self, db_session: AsyncSession
    ):
        creator, colleague = uuid.uuid4(), uuid.uuid4()
        lineup = await self._create(db_session, creator)
        db_session.add(
            TeamMember(team_id=lineup.team_id, user_id=colleague, role="member")
        )
        await db_session.commit()
        found = await saved_lineup_repo.get_saved_lineup(
            db_session, lineup_id=lineup.id, user_id=colleague
        )
        assert found is not None and found.created_by == creator

    async def test_list_saved_lineups_only_shows_my_teams(
        self, db_session: AsyncSession
    ):
        user = uuid.uuid4()
        mine = await self._create(db_session, user)
        await self._create(db_session, uuid.uuid4())
        items, total = await saved_lineup_repo.list_saved_lineups(
            db_session, user_id=user
        )
        assert (total, [i.id for i in items]) == (1, [mine.id])

    async def test_list_can_be_narrowed_to_one_workspace(
        self, db_session: AsyncSession
    ):
        user = uuid.uuid4()
        first = await self._create(db_session, user)
        await self._create(db_session, user)
        items, total = await saved_lineup_repo.list_saved_lineups(
            db_session, user_id=user, team_id=first.team_id
        )
        assert (total, [i.id for i in items]) == (1, [first.id])


class TestUpdateSavedLineup:
    """PUT /lineups/saved/{id} (#290): an edit replaces the content in place, re-resolves roster
    ids like a create, and refuses a stale `expected_updated_at` with 409."""

    async def _setup(self, async_client: AsyncClient) -> tuple[dict, dict, dict]:
        team = await _create_team(async_client)
        player = await _create_player(async_client)
        created = await async_client.post(
            "/lineups/saved", json=_lineup_payload(team["id"], player["id"])
        )
        assert created.status_code == 201
        return team, player, created.json()

    @staticmethod
    def _edit_body(lineup: dict, **changes) -> dict:
        """An edit body from a loaded lineup: its content as the creator would send it."""
        body = {
            "source_team_id": lineup["source_team_id"],
            "opponent_name": lineup["opponent_name"],
            "division": lineup["division"],
            "cap": lineup["cap"],
            "date": lineup["date"],
            "coach": lineup["coach"],
            "players": [
                {
                    "source_player_id": p["source_player_id"],
                    "cap_number": p["cap_number"],
                }
                for p in lineup["players"]
            ],
            "expected_updated_at": lineup["updated_at"],
        }
        return body | changes

    async def _put(self, async_client: AsyncClient, lineup: dict, **changes):
        return await async_client.put(
            f"/lineups/saved/{lineup['id']}", json=self._edit_body(lineup, **changes)
        )

    async def test_a_new_lineup_has_updated_at_equal_to_created_at(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        assert lineup["updated_at"] == lineup["created_at"]

    async def test_an_edit_changes_the_lineup_in_place(self, async_client: AsyncClient):
        team, _, lineup = await self._setup(async_client)
        response = await self._put(
            async_client, lineup, coach="Új Edző", division="OB I.", doctor=None
        )
        assert response.status_code == 200, response.text
        edited = response.json()
        assert edited["id"] == lineup["id"]
        assert edited["team_id"] == team["id"]
        assert (edited["coach"], edited["division"]) == ("Új Edző", "OB I.")
        assert edited["doctor"] is None
        assert edited["created_at"] == lineup["created_at"]
        assert edited["updated_at"] > lineup["updated_at"]
        fetched = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        assert fetched == edited
        listed = (await async_client.get("/lineups/saved")).json()
        assert listed["total"] == 1
        assert listed["items"][0]["coach"] == "Új Edző"

    async def test_the_player_list_replaces_every_old_slot(
        self, async_client: AsyncClient
    ):
        _, player, lineup = await self._setup(async_client)
        other = await _create_player(async_client, "Kiss Béla", "MVLSZ002")
        # the old cap 1 goes to someone else and the old player moves to cap 2
        players = [
            {"source_player_id": other["id"], "cap_number": 1},
            {"source_player_id": player["id"], "cap_number": 2},
            {"name": "Szabó Ádám", "nssz_number": "FREE01", "cap_number": 13},
        ]
        response = await self._put(async_client, lineup, players=players)
        assert response.status_code == 200, response.text
        slots = [
            (p["cap_number"], p["name"], p["nssz_number"])
            for p in response.json()["players"]
        ]
        assert slots == [
            (1, "Kiss Béla", "MVLSZ002"),
            (2, "Török András", "MVLSZ001"),
            (13, "Szabó Ádám", "FREE01"),
        ]
        old_ids = {p["id"] for p in lineup["players"]}
        assert not old_ids & {p["id"] for p in response.json()["players"]}

    async def test_a_roster_player_is_re_frozen_with_their_current_values(
        self, async_client: AsyncClient
    ):
        team, player, lineup = await self._setup(async_client)
        renamed = await async_client.put(
            f"/players/{player['id']}",
            json={
                "name": "Török Bence",
                "nssz_number": "MVLSZ009",
                "team_id": team["id"],
            },
        )
        assert renamed.status_code == 200
        unchanged = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        assert unchanged["players"][0]["name"] == "Török András"

        edited = (await self._put(async_client, unchanged)).json()
        assert edited["players"][0]["name"] == "Török Bence"
        assert edited["players"][0]["nssz_number"] == "MVLSZ009"
        assert edited["players"][0]["source_player_id"] == player["id"]

    async def test_a_slot_whose_player_was_deleted_stays_as_typed_text(
        self, async_client: AsyncClient
    ):
        _, player, lineup = await self._setup(async_client)
        assert (
            await async_client.delete(f"/players/{player['id']}")
        ).status_code == 204
        loaded = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        slot = loaded["players"][0]
        assert slot["source_player_id"] is None
        players = [
            {
                "name": slot["name"],
                "nssz_number": slot["nssz_number"],
                "cap_number": slot["cap_number"],
            }
        ]
        response = await self._put(async_client, loaded, players=players)
        assert response.status_code == 200, response.text
        edited = response.json()["players"][0]
        assert (edited["name"], edited["nssz_number"]) == ("Török András", "MVLSZ001")
        assert edited["source_player_id"] is None

    async def test_a_deleted_roster_player_cannot_be_picked(
        self, async_client: AsyncClient
    ):
        _, player, lineup = await self._setup(async_client)
        await async_client.delete(f"/players/{player['id']}")
        response = await self._put(async_client, lineup)
        assert response.status_code == 404
        unchanged = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        assert unchanged["updated_at"] == lineup["updated_at"]

    async def test_a_stale_version_is_409_and_changes_nothing(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        first = await self._put(async_client, lineup, coach="First Editor")
        assert first.status_code == 200
        second = await self._put(async_client, lineup, coach="Second Editor")
        assert second.status_code == 409
        detail = second.json()["detail"]
        assert "Reload" in detail
        assert "First Editor" not in detail and first.json()["updated_at"] not in detail
        current = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        assert current == first.json()

    async def test_the_same_instant_in_another_offset_is_accepted(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        utc = datetime.fromisoformat(lineup["updated_at"])
        local = utc.astimezone(timezone(timedelta(hours=1))).isoformat()
        response = await self._put(async_client, lineup, expected_updated_at=local)
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize(
        "expected", [None, "2026-11-24T10:00:00", "not a time"], ids=str
    )
    async def test_a_missing_or_naive_version_is_422(
        self, async_client: AsyncClient, expected
    ):
        _, _, lineup = await self._setup(async_client)
        body = self._edit_body(lineup)
        if expected is None:
            body.pop("expected_updated_at")
        else:
            body["expected_updated_at"] = expected
        response = await async_client.put(f"/lineups/saved/{lineup['id']}", json=body)
        assert response.status_code == 422

    async def test_a_concurrent_edit_between_check_and_write_is_409(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Another member's edit commits while this one is resolving its players: the
        compare-and-swap in the repository sees it and nothing of this edit is written."""
        _, _, lineup = await self._setup(async_client)
        real_resolve = saved_lineup_service._resolve_content

        async def resolve_then_someone_else_saves(*args, **kwargs):
            resolved = await real_resolve(*args, **kwargs)
            await db_session.execute(
                update(SavedLineup)
                .where(SavedLineup.id == uuid.UUID(lineup["id"]))
                .values(coach="Other Member", updated_at=datetime.now(UTC))
            )
            await db_session.commit()
            return resolved

        with patch.object(
            saved_lineup_service, "_resolve_content", resolve_then_someone_else_saves
        ):
            response = await self._put(async_client, lineup, coach="Too Late")
        assert response.status_code == 409
        current = (await async_client.get(f"/lineups/saved/{lineup['id']}")).json()
        assert current["coach"] == "Other Member"
        assert [p["id"] for p in current["players"]] == [
            p["id"] for p in lineup["players"]
        ]

    async def test_unknown_lineup_is_404(self, async_client: AsyncClient):
        _, _, lineup = await self._setup(async_client)
        response = await async_client.put(
            f"/lineups/saved/{uuid.uuid4()}", json=self._edit_body(lineup)
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Saved lineup not found"}

    async def test_a_lineup_of_another_team_is_404(
        self, async_client: AsyncClient, current_user
    ):
        _, _, lineup = await self._setup(async_client)
        current_user.id = uuid.uuid4()
        response = await self._put(async_client, lineup, coach="Intruder")
        assert response.status_code == 404
        assert response.json() == {"detail": "Saved lineup not found"}

    async def test_any_member_of_the_team_may_edit(
        self, async_client: AsyncClient, db_session: AsyncSession, current_user
    ):
        team, _, lineup = await self._setup(async_client)
        creator = current_user.id
        colleague = uuid.uuid4()
        await join_team(db_session, team["id"], colleague)
        current_user.id = colleague
        response = await self._put(async_client, lineup, coach="Colleague")
        assert response.status_code == 200, response.text
        db_session.expire_all()
        row = await db_session.get(SavedLineup, uuid.UUID(lineup["id"]))
        assert row.created_by == creator
        assert row.coach == "Colleague"

    async def test_a_team_id_in_the_body_does_not_move_the_lineup(
        self, async_client: AsyncClient
    ):
        team, _, lineup = await self._setup(async_client)
        other = await _create_team(async_client, "Other")
        response = await self._put(async_client, lineup, team_id=other["id"])
        assert response.status_code == 200
        assert response.json()["team_id"] == team["id"]

    async def test_a_player_of_a_team_i_am_not_in_is_404(
        self, async_client: AsyncClient, current_user
    ):
        _, _, lineup = await self._setup(async_client)
        me = current_user.id
        current_user.id = uuid.uuid4()
        foreign = await _create_player(async_client, "Idegen", "FOREIGN1")
        current_user.id = me
        players = [{"source_player_id": foreign["id"], "cap_number": 1}]
        response = await self._put(async_client, lineup, players=players)
        assert response.status_code == 404
        assert "Idegen" not in response.text

    async def test_a_duplicate_nssz_after_resolution_is_422(
        self, async_client: AsyncClient
    ):
        _, player, lineup = await self._setup(async_client)
        players = [
            {"source_player_id": player["id"], "cap_number": 1},
            {"name": "Másik", "nssz_number": "mvlsz001", "cap_number": 2},
        ]
        response = await self._put(async_client, lineup, players=players)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "changes",
        [
            {"date": None},
            {"players": []},
            {"cap": "Piros"},
            {"opponent_name": None},
            {"players": [{"name": "A", "nssz_number": "1", "cap_number": 1}] * 2},
        ],
        ids=["no date", "no players", "bad cap", "no opponent", "same cap twice"],
    )
    async def test_the_create_rules_apply(self, async_client: AsyncClient, changes):
        _, _, lineup = await self._setup(async_client)
        response = await self._put(async_client, lineup, **changes)
        assert response.status_code == 422

    async def test_the_match_name_is_derived_again(self, async_client: AsyncClient):
        _, _, lineup = await self._setup(async_client)
        edited = (await self._put(async_client, lineup, opponent_name="Szentes")).json()
        assert edited["match_name"] == "SZVTK - Szentes"
        named = (await self._put(async_client, edited, match_name="Kupadöntő")).json()
        assert named["match_name"] == "Kupadöntő"

    async def test_the_structured_date_is_handled_like_a_create(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        dated = (
            await self._put(
                async_client,
                lineup,
                match_date="2026-11-28",
                match_time="18:30:45",
            )
        ).json()
        assert dated["date"] == "2026. 11. 28. 18:30"
        assert (dated["match_date"], dated["match_time"]) == ("2026-11-28", "18:30:00")
        # back to free text: the structured fields are cleared
        typed = (await self._put(async_client, dated, date="november vége")).json()
        assert typed["date"] == "november vége"
        assert (typed["match_date"], typed["match_time"]) == (None, None)
        bad = await self._put(async_client, typed, match_time="18:30")
        assert bad.status_code == 422

    async def test_the_location_is_set_and_cleared(self, async_client: AsyncClient):
        _, _, lineup = await self._setup(async_client)
        located = (
            await self._put(async_client, lineup, location="  Szeged, Tisza uszoda ")
        ).json()
        assert located["location"] == "Szeged, Tisza uszoda"
        cleared = (await self._put(async_client, located, location="  ")).json()
        assert cleared["location"] is None

    async def test_is_home_is_set_changed_and_cleared_by_an_edit(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        assert lineup["is_home"] is None
        home = (await self._put(async_client, lineup, is_home=True)).json()
        assert home["is_home"] is True
        away = (await self._put(async_client, home, is_home=False)).json()
        assert away["is_home"] is False
        unknown = (await self._put(async_client, away, is_home=None)).json()
        assert unknown["is_home"] is None

    async def test_the_generated_document_shows_the_edit(
        self, async_client: AsyncClient
    ):
        _, _, lineup = await self._setup(async_client)
        await self._put(async_client, lineup, coach="Szerkesztett Edző")
        response = await async_client.post(
            f"/lineups/saved/{lineup['id']}/generate?format=docx"
        )
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            assert "Szerkesztett Edző" in z.read("word/document.xml").decode()

    async def test_the_repository_refuses_a_stale_version(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        _, _, lineup = await self._setup(async_client)
        lineup_id = uuid.UUID(lineup["id"])
        stale = datetime.fromisoformat(lineup["updated_at"]) - timedelta(seconds=1)
        snapshot = LineupPlayerSnapshot(
            id=uuid.uuid4(), cap_number=5, name="X", nssz_number="X1"
        )
        result = await saved_lineup_repo.update_saved_lineup(
            db_session,
            lineup_id=lineup_id,
            expected_updated_at=stale,
            fields={"coach": "Nobody"},
            player_snapshots=[snapshot],
        )
        assert result is None
        db_session.expire_all()
        row = await db_session.get(SavedLineup, lineup_id)
        assert row.coach == "Török András"
        assert [s.cap_number for s in row.player_snapshots] == [1]
