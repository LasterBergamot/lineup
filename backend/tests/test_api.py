import copy
import subprocess

import pytest
from unittest.mock import patch

FAKE_PDF = b"%PDF-1.4 fake"


@pytest.fixture(autouse=True)
def mock_pdf_converter():
    with patch(
        "lineup.document.pdf_converter.PdfConverter.convert",
        return_value=FAKE_PDF,
    ):
        yield


def test_create_lineup_success(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "content-disposition" in response.headers


def test_create_lineup_document_is_non_empty(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    assert len(response.content) > 0


def test_create_lineup_document_is_valid_pdf(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    assert response.content[:4] == b"%PDF"


def test_create_lineup_filename_contains_team_and_date(client, valid_payload):
    response = client.post("/lineups", json=valid_payload)
    content_disposition = response.headers["content-disposition"]
    assert valid_payload["team_name"] in content_disposition
    assert valid_payload["date"] in content_disposition


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


MAX_LENGTHS = {
    "match": 200,
    "division": 100,
    "team_name": 120,
    "date": 50,
    "coach": 200,
    "doctor": 200,
    "assistant_coach": 200,
    "team_leader": 200,
    "ball_thrower": 200,
}


@pytest.mark.parametrize(("field", "max_length"), MAX_LENGTHS.items())
def test_create_lineup_field_at_max_length_is_accepted(
    client, valid_payload, field, max_length
):
    valid_payload[field] = "x" * max_length
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 200


@pytest.mark.parametrize(("field", "max_length"), MAX_LENGTHS.items())
def test_create_lineup_field_over_max_length_is_rejected(
    client, valid_payload, field, max_length
):
    valid_payload[field] = "x" * (max_length + 1)
    response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 422
    assert field in response.text


@pytest.mark.parametrize(("field", "max_length"), [("name", 200), ("nssz_number", 50)])
def test_create_lineup_player_field_over_max_length_is_rejected(
    client, valid_payload, field, max_length
):
    valid_payload["players"][0][field] = "x" * (max_length + 1)
    response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 422


def test_create_lineup_player_fields_at_max_length_are_accepted(client, valid_payload):
    valid_payload["players"][0]["name"] = "x" * 200
    valid_payload["players"][0]["nssz_number"] = "x" * 50
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 200


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


def test_create_lineup_docx_format_returns_docx(client, valid_payload):
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.status_code == 200
    assert "wordprocessingml" in response.headers["content-type"]
    assert "content-disposition" in response.headers


def test_create_lineup_docx_format_is_valid_docx(client, valid_payload):
    response = client.post("/lineups?format=docx", json=valid_payload)
    assert response.content[:2] == b"PK"


def test_create_lineup_docx_filename_contains_team_and_date(client, valid_payload):
    response = client.post("/lineups?format=docx", json=valid_payload)
    content_disposition = response.headers["content-disposition"]
    assert valid_payload["team_name"] in content_disposition
    assert valid_payload["date"] in content_disposition
    assert content_disposition.endswith(".docx")


def test_create_lineup_conversion_timeout_returns_504(client, valid_payload):
    with patch(
        "lineup.document.pdf_converter.PdfConverter.convert",
        side_effect=subprocess.TimeoutExpired(cmd="libreoffice", timeout=120),
    ):
        response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 504
    assert response.json()["detail"] == "PDF conversion timed out"


def test_create_lineup_unexpected_error_returns_500(client, valid_payload):
    with patch(
        "lineup.api.file_response.WaterPoloLineupCreator",
        side_effect=RuntimeError("forced"),
    ):
        response = client.post("/lineups", json=valid_payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "Document generation failed"


def test_create_lineup_non_latin1_team_name_returns_utf8_filename(
    client, valid_payload
):
    payload = copy.deepcopy(valid_payload)
    payload["team_name"] = 'Szőreg "Ű";'
    response = client.post("/lineups", json=payload)
    assert response.status_code == 200
    content_disposition = response.headers["content-disposition"]
    assert 'filename="rajtlista_Szoreg _U__' in content_disposition
    assert "filename*=UTF-8''rajtlista_Sz%C5%91reg%20%22%C5%B0%22%3B_" in (
        content_disposition
    )
