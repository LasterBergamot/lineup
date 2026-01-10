"""Flask application factory."""

from flask import Flask
from flask_cors import CORS


def create_app(config_name="development"):
    """
    Create and configure the Flask application.

    Args:
        config_name: Configuration environment name (development, testing, production)

    Returns:
        Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f"config.{config_name.capitalize()}Config")

    # Validate production configuration
    if config_name == "production" and not app.config.get("SECRET_KEY"):
        raise ValueError("SECRET_KEY environment variable must be set in production")

    # Initialize CORS with environment-aware configuration
    cors_origins = app.config.get("CORS_ORIGINS")

    if config_name == "production":
        # Production: CORS_ORIGINS must be explicitly set (no wildcard)
        if not cors_origins:
            raise ValueError(
                "CORS_ORIGINS environment variable must be set in production. "
                "Cannot use wildcard (*) in production for security reasons."
            )
        if cors_origins == "*":
            raise ValueError(
                "CORS_ORIGINS cannot be '*' in production. "
                "Please specify exact origins, e.g., 'https://yourdomain.com'"
            )
        # Split comma-separated origins if it's a string
        if isinstance(cors_origins, str):
            cors_origins = [origin.strip() for origin in cors_origins.split(",")]
        CORS(app, origins=cors_origins)
    else:
        # Development/Testing: Allow wildcard or specific origins
        if cors_origins == "*" or cors_origins is None:
            CORS(app)  # Allow all origins
        else:
            # Split comma-separated origins if it's a string
            if isinstance(cors_origins, str):
                cors_origins = [origin.strip() for origin in cors_origins.split(",")]
            CORS(app, origins=cors_origins)

    # Register blueprints
    from app.routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app
