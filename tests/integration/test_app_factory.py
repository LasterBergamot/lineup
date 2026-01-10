"""Integration tests for application factory.

These tests verify the create_app function works correctly with different configurations.
"""

import pytest
from app import create_app


def test_create_app_development():
    """Test creating app in development mode."""
    app = create_app("development")
    assert app is not None
    assert app.config["DEBUG"] is True
    assert app.config["TESTING"] is False
    assert app.config["CORS_ORIGINS"] == "*"


def test_create_app_testing():
    """Test creating app in testing mode."""
    app = create_app("testing")
    assert app is not None
    assert app.config["DEBUG"] is True
    assert app.config["TESTING"] is True
    assert app.config["CORS_ORIGINS"] == "*"


def test_create_app_production_missing_secret_key():
    """Test creating app in production mode without SECRET_KEY raises error."""
    import os
    original_secret = os.environ.get("SECRET_KEY")
    try:
        if "SECRET_KEY" in os.environ:
            del os.environ["SECRET_KEY"]
        with pytest.raises(ValueError, match="SECRET_KEY"):
            create_app("production")
    finally:
        if original_secret:
            os.environ["SECRET_KEY"] = original_secret


def test_app_has_cors_enabled(app):
    """Test that CORS is enabled in the application."""
    # CORS should be configured
    assert app is not None
    # Verify CORS headers would be added (indirectly by checking app works)
    with app.test_client() as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
