"""Tests for health check endpoint."""

import pytest
from app import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app("testing")
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "lineup-api"
    assert "version" in data
