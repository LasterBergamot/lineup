"""End-to-end tests for API flows.

These tests simulate complete user scenarios and test the entire system.
"""


def test_health_check_e2e(client):
    """
    E2E test: Complete flow of checking API health.

    This test simulates a real user checking if the API is healthy.
    """
    # Simulate user making a request
    response = client.get("/api/v1/health")

    # Verify the complete response
    assert response.status_code == 200
    assert response.content_type == "application/json"

    data = response.get_json()
    assert data is not None
    assert "status" in data
    assert "service" in data
    assert "version" in data

    # Verify response structure matches expected format
    assert data["status"] == "healthy"
    assert data["service"] == "lineup-api"
    assert isinstance(data["version"], str)


def test_api_base_path(client):
    """
    E2E test: Verify API base path structure.

    This test ensures the API is properly structured and accessible.
    """
    # Test that API is accessible at the expected base path
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    # Test that non-existent endpoints return 404
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404

    # Test that root path doesn't expose API (if not configured)
    response = client.get("/")
    # This might return 404 or redirect, both are acceptable
    assert response.status_code in [404, 302, 301]
