"""Pytest configuration and shared fixtures."""

import pytest
from app import create_app


@pytest.fixture
def app():
    """Create application instance for testing."""
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()
