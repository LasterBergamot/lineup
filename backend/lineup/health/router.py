"""`GET /health`: liveness and readiness probes for the container, deploys and uptime checks."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lineup.db.engine import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Body of the health endpoint: `ok`, or `unavailable` when the database check failed."""

    status: Literal["ok", "unavailable"]


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
async def health(
    db: Annotated[
        bool,
        Query(
            description="Also check the database (readiness). Default: liveness only."
        ),
    ] = False,
    session: AsyncSession = Depends(get_session),
) -> HealthResponse | JSONResponse:
    """Liveness by default; `?db=1` adds a `SELECT 1` readiness probe.

    A failing probe returns a plain 503 body instead of raising, so the driver's error
    text (which can contain hostnames) never reaches the client and health checks don't
    flood Sentry.
    """
    if db:
        try:
            await session.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("Database health check failed: %s", type(exc).__name__)
            return JSONResponse(status_code=503, content={"status": "unavailable"})
    return HealthResponse(status="ok")
