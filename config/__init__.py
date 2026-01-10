"""Configuration module."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Flask configuration
    SECRET_KEY: Optional[str] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # API configuration
    API_VERSION: str = "v1"
    API_PREFIX: str = f"/api/{API_VERSION}"

    # CORS configuration - should be set explicitly in production
    CORS_ORIGINS: Optional[str] = None


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG: bool = True
    TESTING: bool = False

    # Allow all origins in development (convenient for local development)
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG: bool = True
    TESTING: bool = True
    SECRET_KEY: str = "test-secret-key"

    # Allow all origins in testing (convenient for test suite)
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: Optional[str] = os.environ.get("SECRET_KEY") or None

    # CORS_ORIGINS must be explicitly set in production (no wildcard allowed)
    CORS_ORIGINS: Optional[str] = os.environ.get("CORS_ORIGINS")
