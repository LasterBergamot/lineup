"""Configuration module."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Flask configuration
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # API configuration
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"

    # CORS configuration - should be set explicitly in production
    CORS_ORIGINS = None


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False

    # Allow all origins in development (convenient for local development)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = True
    TESTING = True
    SECRET_KEY = "test-secret-key"

    # Allow all origins in testing (convenient for test suite)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or None

    # CORS_ORIGINS must be explicitly set in production (no wildcard allowed)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS")
