import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


async def handle_integrity_error(
    _request: Request, exc: IntegrityError
) -> JSONResponse:
    """Backstop so a constraint violation that slips past the service checks (for example a
    team deleted between the existence check and the commit) is a 409, not a 500.

    Only the exception classes are logged: SQLAlchemy's message embeds the SQL parameters,
    which are player names and NSSZ numbers.
    """
    logger.warning(
        "Integrity error: %s (%s)", type(exc).__name__, type(exc.orig).__name__
    )
    return JSONResponse(
        status_code=409,
        content={"detail": "The request conflicts with existing data"},
    )
