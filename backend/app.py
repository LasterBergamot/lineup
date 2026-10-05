import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lineup.api.router import router as lineup_router
from lineup.db.base import Base
from lineup.db.engine import engine
from lineup.health.router import router as health_router
from lineup.players.router import router as players_router
from lineup.saved_lineups.router import router as saved_lineups_router
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
    # Dev / test: create all tables from ORM models directly.
    # Production: Alembic handles all DDL — set ENV=production to skip this.
    if os.getenv("ENV") != "production":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Lineup API",
    description="Generates water polo lineup documents.",
    version="0.1.0",
    lifespan=lifespan,
)

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

app.include_router(health_router)
app.include_router(lineup_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(saved_lineups_router)
