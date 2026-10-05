"""Row Level Security and least-privilege checks against a real Postgres.

Skipped unless POSTGRES_TEST_URL points at a *throwaway, empty* Postgres database
(`postgresql+asyncpg://user:password@host:port/db`, a superuser-ish owner). CI's
"Migrations (Postgres)" job sets it; locally:

    docker run -d --name pg -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:17
    POSTGRES_TEST_URL=postgresql+asyncpg://postgres:postgres@localhost:55432/postgres \
        uv run pytest tests/test_postgres_migrations.py

SQLite can't prove any of this: RLS, roles, grants and event triggers are Postgres features,
and the migration is a no-op there.
"""

import os
import secrets
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from lineup.db import app_role

POSTGRES_URL = os.getenv("POSTGRES_TEST_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="POSTGRES_TEST_URL is not set (needs a real Postgres)"
)

APP_TABLES = [
    "lineup_player_snapshots",
    "players",
    "saved_lineups",
    "team_invitations",
    "team_members",
    "teams",
]


@pytest.fixture(scope="module", autouse=True)
def migrated():
    """Fresh database: create Supabase's Data API roles first (so the revoke path runs),
    then migrate to head exactly like `task migrate` does."""
    import asyncio

    async def create_supabase_roles():
        engine = create_async_engine(POSTGRES_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            for role in ("anon", "authenticated"):
                await conn.execute(
                    text(
                        "DO $$ BEGIN IF NOT EXISTS "
                        f"(SELECT FROM pg_roles WHERE rolname = '{role}') "
                        f"THEN CREATE ROLE {role} NOLOGIN; END IF; END $$"
                    )
                )
        await engine.dispose()

    asyncio.run(create_supabase_roles())
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env={**os.environ, "MIGRATE_DATABASE_URL": POSTGRES_URL},
    )


@pytest.fixture
async def engine():
    engine = create_async_engine(POSTGRES_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


async def _rows(engine, sql, **params):
    async with engine.connect() as conn:
        return (await conn.execute(text(sql), params)).all()


class TestRowLevelSecurity:
    async def test_every_public_table_has_rls_enabled(self, engine):
        rows = await _rows(
            engine,
            """SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                 AND NOT c.relrowsecurity""",
        )
        assert rows == [], f"tables without RLS: {[r[0] for r in rows]}"

    async def test_the_migration_history_table_is_covered_too(self, engine):
        rows = await _rows(
            engine,
            "SELECT relrowsecurity FROM pg_class WHERE relname = 'alembic_version'",
        )
        assert rows == [(True,)]

    async def test_event_trigger_exists(self, engine):
        rows = await _rows(
            engine,
            "SELECT evtevent FROM pg_event_trigger WHERE evtname = 'lineup_enable_rls'",
        )
        assert rows == [("ddl_command_end",)]

    async def test_the_trigger_function_has_a_pinned_search_path(self, engine):
        rows = await _rows(
            engine,
            "SELECT proconfig FROM pg_proc WHERE proname = 'lineup_enable_rls'",
        )
        assert rows == [(['search_path=""'],)]

    async def test_a_table_created_later_gets_rls_automatically(self, engine):
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE public.rls_probe (id int)"))
            try:
                enabled = await conn.scalar(
                    text(
                        "SELECT relrowsecurity FROM pg_class WHERE relname = 'rls_probe'"
                    )
                )
            finally:
                await conn.execute(text("DROP TABLE public.rls_probe"))
        assert enabled is True


class TestAppRole:
    async def test_role_is_not_privileged_and_owns_nothing(self, engine):
        [(superuser, bypass_rls, createrole)] = await _rows(
            engine,
            "SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles "
            "WHERE rolname = 'lineup_app'",
        )
        assert (superuser, bypass_rls, createrole) == (False, False, False)
        owned = await _rows(
            engine, "SELECT tablename FROM pg_tables WHERE tableowner = 'lineup_app'"
        )
        assert owned == []

    async def test_dml_on_app_tables_but_not_on_the_migration_history(self, engine):
        for table in APP_TABLES:
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                [(granted,)] = await _rows(
                    engine,
                    "SELECT has_table_privilege('lineup_app', :t, :p)",
                    t=f"public.{table}",
                    p=privilege,
                )
                assert granted, f"lineup_app lacks {privilege} on {table}"
        [(can_read,)] = await _rows(
            engine,
            "SELECT has_table_privilege('lineup_app', 'public.alembic_version', 'SELECT')",
        )
        assert can_read is False

    async def test_schema_changes_are_not_allowed(self, engine):
        [(can_create,)] = await _rows(
            engine, "SELECT has_schema_privilege('lineup_app', 'public', 'CREATE')"
        )
        assert can_create is False

    async def test_app_can_work_through_rls_and_cannot_touch_migration_history(
        self, engine
    ):
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL ROLE lineup_app"))
            await conn.execute(
                text(
                    "INSERT INTO teams (id, name, created_by, is_public, created_at) "
                    "VALUES (gen_random_uuid(), 'RLS probe', gen_random_uuid(), true, now())"
                )
            )
            assert await conn.scalar(text("SELECT count(*) FROM teams")) == 1
            await conn.execute(text("DELETE FROM teams"))
        with pytest.raises(DBAPIError, match="permission denied"):
            async with engine.begin() as conn:
                await conn.execute(text("SET LOCAL ROLE lineup_app"))
                await conn.execute(text("SELECT * FROM alembic_version"))

    async def test_app_can_use_the_team_membership_tables(self, engine):
        """The new tables need their own policy: RLS denies the app until one exists."""
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL ROLE lineup_app"))
            await conn.execute(
                text(
                    "INSERT INTO teams (id, name, created_by, is_public, created_at) "
                    "VALUES ('00000000-0000-0000-0000-000000000001', 'T', "
                    "gen_random_uuid(), true, now())"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO team_members (team_id, user_id, role, joined_at) "
                    "VALUES ('00000000-0000-0000-0000-000000000001', "
                    "gen_random_uuid(), 'owner', now())"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO team_invitations (id, team_id, invited_by, "
                    "invite_code_hash, role, expires_at, created_at) VALUES "
                    "(gen_random_uuid(), '00000000-0000-0000-0000-000000000001', "
                    "gen_random_uuid(), repeat('a', 64), 'member', now(), now())"
                )
            )
            assert await conn.scalar(text("SELECT count(*) FROM team_members")) == 1
            assert await conn.scalar(text("SELECT count(*) FROM team_invitations")) == 1
            await conn.execute(text("DELETE FROM teams"))
            # ON DELETE CASCADE removed the dependants as well
            assert await conn.scalar(text("SELECT count(*) FROM team_members")) == 0

    async def test_a_new_table_denies_the_app_until_a_policy_exists(self, engine):
        """Default privileges hand the app DML on new tables, RLS keeps it out."""
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE public.policy_probe (id int)"))
            try:
                await conn.execute(text("SET LOCAL ROLE lineup_app"))
                assert await conn.scalar(text("SELECT count(*) FROM policy_probe")) == 0
                with pytest.raises(DBAPIError, match="row-level security"):
                    async with conn.begin_nested():
                        await conn.execute(text("INSERT INTO policy_probe VALUES (1)"))
            finally:
                await conn.execute(text("RESET ROLE"))
                await conn.execute(text("DROP TABLE public.policy_probe"))


class TestSupabaseApiRoles:
    @pytest.mark.parametrize("role", ["anon", "authenticated"])
    async def test_data_api_roles_have_no_access_to_any_table(self, engine, role):
        for table in [*APP_TABLES, "alembic_version"]:
            [(granted,)] = await _rows(
                engine,
                "SELECT has_table_privilege(:r, :t, 'SELECT') "
                "OR has_table_privilege(:r, :t, 'INSERT')",
                r=role,
                t=f"public.{table}",
            )
            assert granted is False, f"{role} can reach {table}"

    async def test_a_table_created_later_is_closed_to_them_as_well(self, engine):
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE public.api_probe (id int)"))
            try:
                leaked = await conn.scalar(
                    text(
                        "SELECT has_table_privilege('anon', 'public.api_probe', 'SELECT') "
                        "OR has_table_privilege('authenticated', 'public.api_probe', 'SELECT')"
                    )
                )
            finally:
                await conn.execute(text("DROP TABLE public.api_probe"))
        assert leaked is False


class TestCreateAppRoleTask:
    async def test_the_generated_password_really_lets_the_role_log_in(self, engine):
        generated = secrets.token_hex(12)
        await app_role.set_role_password(POSTGRES_URL, generated)

        url = make_url(POSTGRES_URL).set(username="lineup_app", password=generated)
        app_engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with app_engine.connect() as conn:
                assert await conn.scalar(text("SELECT current_user")) == "lineup_app"
        finally:
            await app_engine.dispose()
