"""Application entry point.

WARNING: This file is intended for local development only.
For production deployments, use a WSGI server (gunicorn, waitress, etc.)
and set FLASK_ENV=production explicitly.
"""

import os
import sys
from app import create_app

# Get environment from .env file or default to development
config_name = os.environ.get("FLASK_ENV", "development").lower()
app = create_app(config_name)

if __name__ == "__main__":
    # Safety check: Warn if running in development mode
    if config_name == "development":
        print(
            "⚠️  WARNING: Running in DEVELOPMENT mode\n",
            file=sys.stderr
        )
    
    # Additional safety: Warn if SECRET_KEY is using default value
    if app.config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
        print(
            "⚠️  WARNING: Using default SECRET_KEY.\n",
            file=sys.stderr
        )
    
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))
