"""Database engine, session factory and the connection quirks of SQLite and Supabase Postgres.

`DATABASE_URL` picks the database (local SQLite file by default). Everything dialect-specific
(foreign keys on SQLite) is confined to this module; the URL-dependent settings live in
`connection_settings.py` so Alembic can use them without creating the app's engine.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lineup.db.connection_settings import make_engine_kwargs

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


engine = create_async_engine(
    DATABASE_URL, echo=False, **make_engine_kwargs(DATABASE_URL)
)
enable_sqlite_foreign_keys(engine)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one `AsyncSession` per request, closed when the request ends.

    Nothing is committed automatically; the repositories commit their own writes.
    """
    async with AsyncSessionLocal() as session:
        yield session
