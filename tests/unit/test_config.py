"""Unit tests for configuration classes.

These tests verify configuration classes work correctly in isolation.
"""

import os
from config import Config, DevelopmentConfig, TestingConfig, ProductionConfig


class TestConfig:
    """Test base Config class."""

    def test_config_defaults(self):
        """Test that Config has expected default values."""
        assert Config.DEBUG is False
        assert Config.TESTING is False
        assert Config.API_VERSION == "v1"
        assert Config.API_PREFIX == "/api/v1"
        assert Config.CORS_ORIGINS is None

    def test_secret_key_has_default(self):
        """Test that SECRET_KEY has a default value."""
        assert Config.SECRET_KEY is not None
        assert isinstance(Config.SECRET_KEY, str)


class TestDevelopmentConfig:
    """Test DevelopmentConfig class."""

    def test_development_debug_enabled(self):
        """Test that development mode has DEBUG enabled."""
        assert DevelopmentConfig.DEBUG is True
        assert DevelopmentConfig.TESTING is False

    def test_development_cors_allows_all(self):
        """Test that development mode allows all origins by default."""
        assert DevelopmentConfig.CORS_ORIGINS == "*"


class TestTestingConfig:
    """Test TestingConfig class."""

    def test_testing_mode_enabled(self):
        """Test that testing mode has TESTING enabled."""
        assert TestingConfig.DEBUG is True
        assert TestingConfig.TESTING is True

    def test_testing_secret_key(self):
        """Test that testing mode has a test secret key."""
        assert TestingConfig.SECRET_KEY == "test-secret-key"

    def test_testing_cors_allows_all(self):
        """Test that testing mode allows all origins by default."""
        assert TestingConfig.CORS_ORIGINS == "*"


class TestProductionConfig:
    """Test ProductionConfig class."""

    def test_production_debug_disabled(self):
        """Test that production mode has DEBUG disabled."""
        assert ProductionConfig.DEBUG is False
        assert ProductionConfig.TESTING is False

    def test_production_cors_requires_setting(self):
        """Test that production mode requires CORS_ORIGINS to be set."""
        # CORS_ORIGINS should be None by default (must be set explicitly)
        assert ProductionConfig.CORS_ORIGINS is None or ProductionConfig.CORS_ORIGINS == os.environ.get(
            "CORS_ORIGINS"
        )
