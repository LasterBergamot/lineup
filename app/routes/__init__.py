"""API routes blueprint."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import routes to register them
from app.routes import health  # noqa: E402, F401
