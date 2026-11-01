import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import app
from lineup.auth.dependencies import get_current_user_id
from lineup.db.base import Base
from lineup.db.connection_settings import make_engine_kwargs
from lineup.db.engine import enable_sqlite_foreign_keys, get_session
from lineup.security.rate_limit import reset_limiters

# ── Sync fixtures (used by test_api.py) ───────────────────────────────────────


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """The limiters keep their counters in module state: start every test from zero."""
    reset_limiters()
    yield
    reset_limiters()


@pytest.fixture
def client(current_user):
    """A TestClient signed in as `current_user` (POST /lineups needs a token).

    Tests that need an anonymous caller build `TestClient(app)` themselves.
    """
    app.dependency_overrides[get_current_user_id] = lambda: current_user.id
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user_id, None)


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
            {
                "cap_number": i,
                "name": "Török András",
                "nssz_number": f"MVLSZ{123456788 + i}",
            }
            for i in range(1, 16)
        ],
    }


# ── Async DB fixtures (used by test_teams, test_players, test_saved_lineups) ──

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Set to a *throwaway* Postgres database (`postgresql+asyncpg://…`) to run the whole suite against
# it instead of in-memory SQLite (#38). CI's "Backend on Postgres" job does; locally:
#   docker run -d --rm -e POSTGRES_PASSWORD=postgres -p 55433:5432 postgres:17
#   TEST_POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:55433/postgres uv run pytest
# Its tables are dropped and rebuilt from the models at the start of the run and emptied after
# every test, so never point it at a database you care about.
POSTGRES_SUITE_URL = os.getenv("TEST_POSTGRES_URL")


def _all_tables_sql() -> str:
    return ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)


@pytest.fixture(scope="session", autouse=True)
def _postgres_schema():
    """With `TEST_POSTGRES_URL` set, start the session from a freshly built schema."""
    if not POSTGRES_SUITE_URL:
        return

    async def rebuild() -> None:
        engine = create_async_engine(
            POSTGRES_SUITE_URL, **make_engine_kwargs(POSTGRES_SUITE_URL)
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(rebuild())


@pytest.fixture
async def db_engine():
    """A database engine for one test: in-memory SQLite, or the Postgres of
    `TEST_POSTGRES_URL` (emptied again afterwards)."""
    if POSTGRES_SUITE_URL:
        engine = create_async_engine(
            POSTGRES_SUITE_URL, **make_engine_kwargs(POSTGRES_SUITE_URL)
        )
        yield engine
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_all_tables_sql()} CASCADE"))
        await engine.dispose()
        return
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


class CurrentUser:
    """The user the test client is signed in as. Assign `.id` mid-test to switch users."""

    def __init__(self) -> None:
        self.id = uuid.uuid4()


@pytest.fixture
def current_user() -> CurrentUser:
    """A fresh signed-in user for the `async_client` of this test."""
    return CurrentUser()


@pytest.fixture
async def async_client(
    db_engine, db_session: AsyncSession, current_user: CurrentUser
) -> AsyncClient:
    """
    AsyncClient wired to the FastAPI app with dependency overrides:
    - get_session → a **new** session per request from the test engine, like production, so
      one request never sees another request's identity map (a shared session hid stale data
      after deletes and would hide a missing rollback after an `IntegrityError`)
    - get_current_user_id → `current_user.id` (no token needed; the real JWT check is
      covered in test_auth_dependencies.py)

    `db_session` is a separate session on the same engine, for tests that arrange or assert
    rows directly: call `db_session.expire_all()` (or use a fresh `select`) before reading
    something an API call changed.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def per_request_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = per_request_session
    app.dependency_overrides[get_current_user_id] = lambda: current_user.id
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
