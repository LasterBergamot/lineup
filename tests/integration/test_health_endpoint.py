"""Integration tests for health check endpoint.

These tests verify the health endpoint works correctly with the Flask application.
"""


def test_health_check(client):
    """Test health check endpoint returns correct response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "lineup-api"
    assert "version" in data


def test_health_check_content_type(client):
    """Test health check endpoint returns JSON content type."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.content_type == "application/json"


def test_health_check_method_not_allowed(client):
    """Test health check endpoint only allows GET method."""
    response = client.post("/api/v1/health")
    assert response.status_code == 405  # Method Not Allowed
