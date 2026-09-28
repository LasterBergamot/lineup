import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lineup.api.router import router as lineup_router
from lineup.db.base import Base
from lineup.db.engine import engine
from lineup.players.router import router as players_router
from lineup.saved_lineups.router import router as saved_lineups_router
from lineup.teams.router import router as teams_router


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

app.include_router(lineup_router)
app.include_router(teams_router)
app.include_router(players_router)
app.include_router(saved_lineups_router)
