import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import app
from lineup.auth.dependencies import get_current_user_id
from lineup.db.base import Base
from lineup.db.engine import enable_sqlite_foreign_keys, get_session

# ── Existing sync fixture (used by test_api.py — kept exactly as before) ──────


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_payload():
    return {
        "match": "SZVTK - Csongrád",
        "division": "OB II.",
        "team_name": "SZVTK",
        "cap": "Fehér",
        "date": "2024. 12. 21.",
        "coach": "Török András",
        "doctor": "Török András",
        "assistant_coach": "Török András",
        "team_leader": "Török András",
        "ball_thrower": "Török András",
        "players": [
            {"cap_number": i, "name": "Török András", "nssz_number": "MVLSZ123456789"}
            for i in range(1, 16)
        ],
    }


# ── Async DB fixtures (used by test_teams, test_players, test_saved_lineups) ──

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    """Creates a fresh in-memory SQLite engine and drops all tables after the test."""
    engine = create_async_engine(TEST_DATABASE_URL)
    enable_sqlite_foreign_keys(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    """Provides a single AsyncSession backed by the in-memory engine."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncClient:
    """
    AsyncClient wired to the FastAPI app with dependency overrides:
    - get_session → in-memory SQLite session
    - get_current_user_id → None (pre-Auth behaviour)
    """
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_current_user_id] = lambda: None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
