import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from lineup.db.base import Base
import lineup.db.models  # noqa: F401 — registers all ORM models with Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Which database to migrate, most specific first:
#   MIGRATE_DATABASE_URL  Supabase direct (or session-pooler) connection as the table owner.
#                         The app's own DATABASE_URL points at the transaction pooler and the
#                         least-privilege `lineup_app` role, which can neither run DDL nor
#                         change the schema, so migrations need their own URL.
#   DATABASE_URL          what `task migrate` / CI set for a throwaway SQLite file
#   alembic.ini           local SQLite default
url = (
    os.getenv("MIGRATE_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
)
config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def compare_type(
    context, inspected_column, metadata_column, inspected_type, metadata_type
):
    """Skip type comparison on SQLite.

    SQLite has no real UUID type: the migration declares `UUID` but reflection reports
    `NUMERIC`, so `alembic check` would flag every UUID column as drifted. Column, FK and
    nullability drift is still checked on SQLite; the Postgres CI job compares types for real.
    """
    if context.dialect.name == "sqlite":
        return False
    return None


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=compare_type,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live DB connection (async)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(
                conn, target_metadata=target_metadata, compare_type=compare_type
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
