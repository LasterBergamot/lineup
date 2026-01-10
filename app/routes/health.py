"""Health check endpoint."""

from flask import jsonify
from app.routes import api_bp


@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.

    Returns:
        JSON response with status information
    """
    return jsonify({"status": "healthy", "service": "lineup-api", "version": "0.1.0"}), 200
