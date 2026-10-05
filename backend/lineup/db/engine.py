"""Database engine, session factory and the connection quirks of SQLite and Supabase Postgres.

`DATABASE_URL` picks the database (local SQLite file by default). Everything dialect-specific
(foreign keys on SQLite, pooler-safe settings on Postgres) is confined to this module.
"""

import os
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./lineup.db",  # file-backed local dev default
)


def enable_sqlite_foreign_keys(async_engine: AsyncEngine) -> None:
    """SQLite ignores FK `ondelete` clauses (SET NULL/RESTRICT/CASCADE) unless
    foreign key enforcement is turned on per-connection — without this, soft
    references like source_team_id/source_player_id never get nulled out.
    No-op on other dialects: `PRAGMA` is SQLite-only syntax and would fail on Postgres."""
    if async_engine.url.get_backend_name() != "sqlite":
        return

    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _unique_statement_name() -> str:
    """Give every prepared statement its own name so pooled connections never collide."""
    return f"__asyncpg_{uuid.uuid4()}__"


def _make_engine_kwargs(database_url: str) -> dict:
    """Postgres (Supabase) sits behind a transaction-mode pooler that already pools
    connections, so SQLAlchemy must not keep its own pool on top of it. The pooler also
    hands the same server connection to different clients, so asyncpg's prepared
    statements must be off (both caches) and any it still names must be unique —
    otherwise requests fail with DuplicatePreparedStatementError."""
    if make_url(database_url).get_backend_name() != "postgresql":
        return {}
    return {
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": _unique_statement_name,
        },
    }


engine = create_async_engine(
    DATABASE_URL, echo=False, **_make_engine_kwargs(DATABASE_URL)
)
enable_sqlite_foreign_keys(engine)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one `AsyncSession` per request, closed when the request ends.

    Nothing is committed automatically; the repositories commit their own writes.
    """
    async with AsyncSessionLocal() as session:
        yield session
