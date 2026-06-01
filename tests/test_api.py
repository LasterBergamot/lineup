import base64
import copy


def test_create_lineup_success(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 200
    body = response.json()
    assert "document" in body
    assert "filename" in body


def test_create_lineup_document_is_non_empty(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    body = response.json()
    assert len(body["document"]) > 0


def test_create_lineup_document_is_valid_docx(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    doc_bytes = base64.b64decode(response.json()["document"])
    assert doc_bytes[:2] == b"PK"


def test_create_lineup_filename_contains_team_and_date(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    filename = response.json()["filename"]
    assert valid_payload["team_name"] in filename
    assert valid_payload["date"] in filename


def test_create_lineup_invalid_cap(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["cap"] = "Piros"
    response = client.post("/lineups", json=payload)
    assert response.status_code == 422


def test_create_lineup_duplicate_cap_numbers(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["players"] = [
        {"cap_number": 1, "name": "Player A", "nssz_number": "MVLSZ000001"},
        {"cap_number": 1, "name": "Player B", "nssz_number": "MVLSZ000002"},
    ]
    response = client.post("/lineups", json=payload)
    assert response.status_code == 422


def test_create_lineup_empty_players(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["players"] = []
    response = client.post("/lineups", json=payload)
    assert response.status_code == 422


def test_create_lineup_cap_number_too_high(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["players"] = [
        {"cap_number": 16, "name": "Player", "nssz_number": "MVLSZ000001"}
    ]
    response = client.post("/lineups", json=payload)
    assert response.status_code == 422


def test_create_lineup_cap_number_zero(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["players"] = [
        {"cap_number": 0, "name": "Player", "nssz_number": "MVLSZ000001"}
    ]
    response = client.post("/lineups", json=payload)
    assert response.status_code == 422


def test_create_lineup_kek_cap(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["cap"] = "Kék"
    response = client.post("/lineups", json=payload)
    assert response.status_code == 200


def test_create_lineup_single_player(client, valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["players"] = [
        {"cap_number": 5, "name": "Test Player", "nssz_number": "MVLSZ999"}
    ]
    response = client.post("/lineups", json=payload)
    assert response.status_code == 200


def test_create_lineup_template_not_found_returns_500(client, valid_payload):
    from unittest.mock import patch

    with patch(
        "lineup.api.router.WaterPoloLineupCreator", side_effect=FileNotFoundError
    ):
        response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "Document template not found"


def test_create_lineup_unexpected_error_returns_500(client, valid_payload):
    from unittest.mock import patch

    with patch(
        "lineup.api.router.WaterPoloLineupCreator", side_effect=RuntimeError("forced")
    ):
        response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "Document generation failed"
