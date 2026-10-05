"""Cross-endpoint input rules: control characters and blank strings (#54), unknown team ids
(#53), the "source id or free text, never both" rule and duplicate NSSZ numbers (#54), and
stable list / snapshot ordering (#55)."""

import copy
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from lineup.common.types import blank_to_none, reject_unsafe_characters

UNSAFE = ["a\x00b", "a\tb", "a\nb", "a\x7fb", "a\x85b"]
BLANK = ["", "   ", "\t \n"]


def _saved_payload(**overrides) -> dict:
    payload = {
        "team_name": "Home Club",
        "opponent_name": "Away Club",
        "division": "OB II.",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Coach",
        "players": [{"name": "Free Player", "nssz_number": "F001", "cap_number": 1}],
    }
    payload.update(overrides)
    return payload


async def _create_team(client: AsyncClient, name: str = "SZVTK") -> dict:
    response = await client.post("/teams", json={"name": name})
    assert response.status_code == 201
    return response.json()


async def _create_player(
    client: AsyncClient, name: str = "Player", nssz: str = "MVLSZ001"
) -> dict:
    response = await client.post("/players", json={"name": name, "nssz_number": nssz})
    assert response.status_code == 201
    return response.json()


class TestSharedStringType:
    @pytest.mark.parametrize("value", [*UNSAFE, "a\ud800b", "a￾b", "a￿b"])
    def test_unsafe_characters_are_rejected(self, value):
        with pytest.raises(ValueError, match="control characters"):
            reject_unsafe_characters(value)

    @pytest.mark.parametrize("value", ["Török András", "Kék", "O'Brien-Smith", "日本"])
    def test_ordinary_text_passes(self, value):
        assert reject_unsafe_characters(value) == value

    @pytest.mark.parametrize("value", BLANK)
    def test_blank_becomes_none(self, value):
        assert blank_to_none(value) is None

    def test_non_blank_and_non_strings_pass_through(self):
        assert blank_to_none(" x ") == " x "
        assert blank_to_none(7) == 7


class TestControlCharactersAndBlanks:
    @pytest.mark.parametrize("value", [*UNSAFE, *BLANK])
    async def test_team_name_rejected_on_create_and_update(
        self, async_client: AsyncClient, value
    ):
        assert (
            await async_client.post("/teams", json={"name": value})
        ).status_code == 422
        team = await _create_team(async_client)
        response = await async_client.put(f"/teams/{team['id']}", json={"name": value})
        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["name", "nssz_number"])
    @pytest.mark.parametrize("value", [*UNSAFE, *BLANK])
    async def test_player_fields_rejected_on_create_and_update(
        self, async_client: AsyncClient, field, value
    ):
        body = {"name": "Player", "nssz_number": "MVLSZ001", field: value}
        assert (await async_client.post("/players", json=body)).status_code == 422
        player = await _create_player(async_client)
        response = await async_client.put(f"/players/{player['id']}", json=body)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "field",
        [
            "match",
            "division",
            "team_name",
            "date",
            "coach",
            "doctor",
            "assistant_coach",
            "team_leader",
            "ball_thrower",
        ],
    )
    @pytest.mark.parametrize("value", [*UNSAFE, *BLANK])
    def test_one_off_lineup_fields_rejected(self, client, valid_payload, field, value):
        valid_payload[field] = value
        assert client.post("/lineups", json=valid_payload).status_code == 422

    @pytest.mark.parametrize("field", ["name", "nssz_number"])
    @pytest.mark.parametrize("value", [*UNSAFE, *BLANK])
    def test_one_off_lineup_player_fields_rejected(
        self, client, valid_payload, field, value
    ):
        valid_payload["players"][0][field] = value
        assert client.post("/lineups", json=valid_payload).status_code == 422

    @pytest.mark.parametrize("field", ["division", "date", "coach"])
    @pytest.mark.parametrize("value", [*UNSAFE, *BLANK])
    async def test_saved_lineup_required_fields_rejected(
        self, async_client: AsyncClient, field, value
    ):
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(**{field: value})
        )
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "field", ["match_name", "doctor", "assistant_coach", "team_leader"]
    )
    @pytest.mark.parametrize("value", UNSAFE)
    async def test_saved_lineup_optional_fields_reject_control_characters(
        self, async_client: AsyncClient, field, value
    ):
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(**{field: value})
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["name", "nssz_number"])
    @pytest.mark.parametrize("value", UNSAFE)
    async def test_saved_lineup_player_free_text_rejects_control_characters(
        self, async_client: AsyncClient, field, value
    ):
        player = {"name": "Free Player", "nssz_number": "F001", "cap_number": 1}
        player[field] = value
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=[player])
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["team_name", "opponent_name"])
    @pytest.mark.parametrize("value", UNSAFE)
    async def test_saved_lineup_team_names_reject_control_characters(
        self, async_client: AsyncClient, field, value
    ):
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(**{field: value})
        )
        assert response.status_code == 422

    async def test_values_are_stripped(self, async_client: AsyncClient):
        team = (await async_client.post("/teams", json={"name": "  SZVTK  "})).json()
        assert team["name"] == "SZVTK"

    async def test_blank_optional_saved_lineup_fields_count_as_not_provided(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/lineups/saved",
            json=_saved_payload(doctor="  ", match_name="", team_leader=""),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["doctor"] is None
        assert data["team_leader"] is None
        assert data["match_name"] == "Home Club - Away Club"

    async def test_blank_team_name_without_source_id_is_rejected(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(team_name="   ")
        )
        assert response.status_code == 422
        assert "team_name" in response.text


class TestSourceIdOrFreeTextNotBoth:
    async def test_player_with_source_id_and_name_is_rejected(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        slot = {"source_player_id": player["id"], "name": "Other", "cap_number": 1}
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=[slot])
        )
        assert response.status_code == 422
        assert "not both" in response.text

    async def test_player_with_source_id_and_nssz_is_rejected(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        slot = {"source_player_id": player["id"], "nssz_number": "X1", "cap_number": 1}
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=[slot])
        )
        assert response.status_code == 422

    async def test_blank_free_text_next_to_a_source_id_is_fine(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client, "Roster Name", "R001")
        slot = {
            "source_player_id": player["id"],
            "name": "  ",
            "nssz_number": "",
            "cap_number": 1,
        }
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=[slot])
        )
        assert response.status_code == 201
        assert response.json()["players"][0]["name"] == "Roster Name"

    @pytest.mark.parametrize("kind", ["team", "opponent"])
    async def test_team_or_opponent_with_source_id_and_name_is_rejected(
        self, async_client: AsyncClient, kind
    ):
        team = await _create_team(async_client)
        response = await async_client.post(
            "/lineups/saved",
            json=_saved_payload(
                **{f"source_{kind}_id": team["id"], f"{kind}_name": "Typed name"}
            ),
        )
        assert response.status_code == 422
        assert f"source_{kind}_id or {kind}_name, not both" in response.text

    async def test_source_team_name_is_always_the_roster_name(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client, "Roster Team")
        response = await async_client.post(
            "/lineups/saved",
            json=_saved_payload(source_team_id=team["id"], team_name=None),
        )
        assert response.json()["team_name"] == "Roster Team"


class TestDuplicateNsszNumbers:
    def test_one_off_lineup_rejects_duplicates_ignoring_case(
        self, client, valid_payload
    ):
        payload = copy.deepcopy(valid_payload)
        payload["players"][1]["nssz_number"] = payload["players"][0][
            "nssz_number"
        ].lower()
        response = client.post("/lineups", json=payload)
        assert response.status_code == 422
        assert "NSSZ" in response.text

    async def test_saved_lineup_rejects_duplicate_free_text_numbers(
        self, async_client: AsyncClient
    ):
        players = [
            {"name": "A", "nssz_number": "SAME", "cap_number": 1},
            {"name": "B", "nssz_number": "same", "cap_number": 2},
        ]
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=players)
        )
        assert response.status_code == 422
        assert "NSSZ" in response.json()["detail"]

    async def test_saved_lineup_rejects_roster_number_equal_to_free_text_number(
        self, async_client: AsyncClient
    ):
        roster = await _create_player(async_client, "Roster", "DUP001")
        players = [
            {"source_player_id": roster["id"], "cap_number": 1},
            {"name": "Typed", "nssz_number": "DUP001", "cap_number": 2},
        ]
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=players)
        )
        assert response.status_code == 422

    async def test_distinct_numbers_are_accepted(self, async_client: AsyncClient):
        players = [
            {"name": "A", "nssz_number": "N1", "cap_number": 1},
            {"name": "B", "nssz_number": "N2", "cap_number": 2},
        ]
        response = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=players)
        )
        assert response.status_code == 201


class TestUnknownTeamId:
    async def test_create_player_with_unknown_team_returns_404(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/players",
            json={
                "name": "P",
                "nssz_number": "N1",
                "team_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Team not found"

    async def test_update_player_with_unknown_team_returns_404_and_keeps_the_player(
        self, async_client: AsyncClient
    ):
        player = await _create_player(async_client)
        response = await async_client.put(
            f"/players/{player['id']}",
            json={"name": "P", "nssz_number": "N1", "team_id": str(uuid.uuid4())},
        )
        assert response.status_code == 404
        unchanged = (await async_client.get(f"/players/{player['id']}")).json()
        assert unchanged["team_id"] is None

    async def test_known_team_is_accepted_on_create_and_update(
        self, async_client: AsyncClient
    ):
        team = await _create_team(async_client)
        created = await async_client.post(
            "/players",
            json={"name": "P", "nssz_number": "N1", "team_id": team["id"]},
        )
        assert created.status_code == 201
        updated = await async_client.put(
            f"/players/{created.json()['id']}",
            json={"name": "P2", "nssz_number": "N1", "team_id": team["id"]},
        )
        assert updated.status_code == 200

    async def test_team_deleted_between_check_and_commit_is_a_409_not_a_500(
        self, async_client: AsyncClient
    ):
        with patch(
            "lineup.players.service.team_repo.get_team",
            AsyncMock(return_value=object()),
        ):
            response = await async_client.post(
                "/players",
                json={
                    "name": "P",
                    "nssz_number": "N1",
                    "team_id": str(uuid.uuid4()),
                },
            )
        assert response.status_code == 409
        assert response.json() == {"detail": "The request conflicts with existing data"}
        assert "INSERT" not in response.text


class TestStableOrdering:
    async def test_teams_are_paged_by_name(self, async_client: AsyncClient):
        for name in ("Delta", "Alpha", "Charlie", "Bravo", "Echo"):
            await _create_team(async_client, name)
        pages = []
        for offset in (0, 2, 4):
            response = await async_client.get(f"/teams?limit=2&offset={offset}")
            pages.append([t["name"] for t in response.json()["items"]])
        assert pages == [["Alpha", "Bravo"], ["Charlie", "Delta"], ["Echo"]]

    async def test_teams_with_the_same_name_are_ordered_by_id(
        self, async_client: AsyncClient
    ):
        ids = [(await _create_team(async_client, "Same"))["id"] for _ in range(4)]
        listed = (await async_client.get("/teams?limit=4")).json()["items"]
        assert [t["id"] for t in listed] == sorted(ids)
        pool = (await async_client.get("/teams/pool")).json()
        assert [t["id"] for t in pool] == sorted(ids)

    async def test_players_are_paged_in_creation_order(self, async_client: AsyncClient):
        for i in range(5):
            await _create_player(async_client, f"Player {i}", f"N{i}")
        pages = []
        for offset in (0, 2, 4):
            response = await async_client.get(f"/players?limit=2&offset={offset}")
            pages.append([p["name"] for p in response.json()["items"]])
        assert pages == [
            ["Player 0", "Player 1"],
            ["Player 2", "Player 3"],
            ["Player 4"],
        ]

    async def test_saved_lineups_are_paged_in_creation_order(
        self, async_client: AsyncClient
    ):
        for i in range(5):
            response = await async_client.post(
                "/lineups/saved", json=_saved_payload(match_name=f"Match {i}")
            )
            assert response.status_code == 201
        pages = []
        for offset in (0, 2, 4):
            response = await async_client.get(f"/lineups/saved?limit=2&offset={offset}")
            pages.append([x["match_name"] for x in response.json()["items"]])
        assert pages == [["Match 0", "Match 1"], ["Match 2", "Match 3"], ["Match 4"]]

    async def test_create_returns_players_in_the_same_order_as_get(
        self, async_client: AsyncClient
    ):
        players = [
            {"name": "Nine", "nssz_number": "N9", "cap_number": 9},
            {"name": "Two", "nssz_number": "N2", "cap_number": 2},
            {"name": "Five", "nssz_number": "N5", "cap_number": 5},
        ]
        created = await async_client.post(
            "/lineups/saved", json=_saved_payload(players=players)
        )
        fetched = await async_client.get(f"/lineups/saved/{created.json()['id']}")
        created_caps = [p["cap_number"] for p in created.json()["players"]]
        assert created_caps == [2, 5, 9]
        assert created_caps == [p["cap_number"] for p in fetched.json()["players"]]
