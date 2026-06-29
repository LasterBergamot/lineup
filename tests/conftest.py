import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_payload():
    return {
        "match": "SZVTK - Csongrád",
        "division": "OB II.",
        "team_name": "SZVTK",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Török András",
        "doctor": "Török András",
        "assistant_coach": "Török András",
        "team_leader": "Török András",
        "ball_thrower": "Török András",
        "players": [
            {"cap_number": i, "name": "Török András", "nssz_number": "MVLSZ123456789"}
            for i in range(1, 16)
        ],
    }
