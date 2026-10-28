"""FastAPI application entry point: wires up the middleware, the error handler, the routers and Sentry.

Run with `uvicorn app:app` (the container does this). Each feature lives in its own package
under `lineup/` (router -> service -> repository) and is registered below.
"""

import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from lineup.api.router import router as lineup_router
from lineup.common.errors import handle_integrity_error
from lineup.db.base import Base
from lineup.db.engine import engine
from lineup.health.router import router as health_router
from lineup.players.router import router as players_router
from lineup.saved_lineups.router import router as saved_lineups_router
from lineup.security.body_limit import BodySizeLimitMiddleware
from lineup.security.config import read_docs_enabled, validate_production_config
from lineup.security.headers import SecurityHeadersMiddleware
from lineup.teams.router import router as teams_router

# Error monitoring only, no performance tracing/APM (traces_sample_rate=0.0) — sized for the
# Sentry free "Developer" tier. SENTRY_DSN unset (local dev, CI, tests) => init is skipped
# entirely, so no network call is ever attempted and nothing is sent anywhere by default.
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.0)


def parse_cors_origins(raw: str | None) -> list[str]:
    """Comma-separated `CORS_ORIGINS` -> explicit origin list (empty = CORS disabled).

    A wildcard is refused on purpose: the allowlist must name every browser origin that may
    call the API (requirement S11), so a typo fails at startup instead of opening it up.
    """
    origins = [o.strip().rstrip("/") for o in (raw or "").split(",") if o.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed")
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check the production config, then create missing tables unless Alembic owns the schema.

    With `ENV=production` the app refuses to start (`ValueError`) when the database or sign-in
    settings are missing or insecure, see `validate_production_config`.

    The tables are created straight from the ORM models for local SQLite and tests. With
    `ENV=production` (any real Postgres, dev or prod) startup leaves the schema alone, because
    Alembic migrations are the only thing allowed to change it there.
    """
    validate_production_config()
    if os.getenv("ENV") != "production":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


# Interactive docs are off in production (and optionally elsewhere via DOCS_ENABLED=false).
# `app.openapi()` still works without the route, which is what scripts/dump_openapi.py uses.
docs_enabled = read_docs_enabled(os.getenv("DOCS_ENABLED"), os.getenv("ENV"))

app = FastAPI(
    title="Lineup API",
    description="Generates water polo lineup documents.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

# Middleware order matters: each add_middleware wraps everything added before it, so the last
# one added is outermost. Body limit innermost, then CORS (so a 413 still gets CORS headers and
# the browser can read it), then the security headers around all of it.
app.add_middleware(BodySizeLimitMiddleware)

cors_origins = parse_cors_origins(os.getenv("CORS_ORIGINS"))
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        # Without this a browser hides the header from fetch(), and the frontend
        # couldn't read the download file name.
        expose_headers=["Content-Disposition"],
        allow_credentials=False,
    )

app.add_middleware(SecurityHeadersMiddleware)

app.add_exception_handler(IntegrityError, handle_integrity_error)

app.include_router(health_router)
app.include_router(lineup_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(saved_lineups_router)
