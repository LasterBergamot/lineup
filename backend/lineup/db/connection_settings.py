"""Connection settings that depend only on the database URL.

Kept apart from `engine.py` on purpose: importing that module creates the application's engine
from `DATABASE_URL`, which `alembic/env.py` must not do (it may migrate a different database).
"""

import uuid

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def _unique_statement_name() -> str:
    """Give every prepared statement its own name so pooled connections never collide."""
    return f"__asyncpg_{uuid.uuid4()}__"


def make_engine_kwargs(database_url: str) -> dict:
    """Postgres (Supabase) sits behind a transaction-mode pooler that already pools
    connections, so SQLAlchemy must not keep its own pool on top of it. The pooler also
    hands the same server connection to different clients, so asyncpg's prepared
    statements must be off (both caches) and any it still names must be unique —
    otherwise requests fail with DuplicatePreparedStatementError.

    Shared by the app's engine and by `alembic/env.py`, so migrations through a pooler get the
    same settings."""
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


def auto_create_schema_enabled(database_url: str, flag: str | None) -> bool:
    """Whether startup may build the tables straight from the ORM models.

    That shortcut is for throw-away SQLite (local runs, the default container). It needs both an
    explicit opt-in (`AUTO_CREATE_SCHEMA=1`/`true`/`yes`) *and* a SQLite database: on Postgres
    Alembic is the only thing allowed to change the schema, whatever the flag says, so a forgotten
    or inherited flag can never create untracked tables there (the next `alembic upgrade` would
    fail with "table already exists").
    """
    opted_in = (flag or "").strip().lower() in {"1", "true", "yes"}
    return opted_in and make_url(database_url).get_backend_name() == "sqlite"
