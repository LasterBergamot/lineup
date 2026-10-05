"""rls_and_least_privilege_role

Postgres only (a no-op on SQLite). Codifies, in one reviewable place, what was done by hand on
the dev Supabase project on 2026-10-02 and adds the least-privilege application role:

1. Row Level Security on every `public` table (RLS with no policy = deny for everyone except
   the table owner and roles with BYPASSRLS).
2. `anon` / `authenticated` (Supabase's Data API roles) lose all access, including on
   tables created later.
3. An event trigger that switches RLS on for every table created in `public` from now on, so
   a forgotten `ENABLE ROW LEVEL SECURITY` can't silently expose a table.
4. The `lineup_app` role the API connects as: not the owner, no BYPASSRLS, DML on the app
   tables only, plus an interim allow-all policy (#21 replaces it with team-scoped ones).

The role is created NOLOGIN here; `task db:create-app-role` gives it a password.

Revision ID: 8b1f3c2d9a47
Revises: 35ce55ceabf4
Create Date: 2026-10-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8b1f3c2d9a47"
down_revision: Union[str, Sequence[str], None] = "35ce55ceabf4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "lineup_app"
# Tables the API reads and writes. alembic_version is deliberately not listed: the app must
# not be able to touch the migration history.
APP_TABLES = ("teams", "players", "saved_lineups", "lineup_player_snapshots")
# Supabase's Data API roles. They don't exist on plain Postgres (CI, local), so every
# statement that names them is guarded.
SUPABASE_API_ROLES = ("anon", "authenticated")

ENABLE_RLS_ON_ALL_PUBLIC_TABLES = """
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END $$;
"""

REVOKE_FROM_SUPABASE_API_ROLES = """
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
      EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM %I', r);
      EXECUTE format(
        'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', r);
      EXECUTE format(
        'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', r);
      EXECUTE format(
        'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I', r);
    END IF;
  END LOOP;
END $$;
"""

ENABLE_RLS_FUNCTION = """
CREATE OR REPLACE FUNCTION public.lineup_enable_rls() RETURNS event_trigger
LANGUAGE plpgsql AS $$
DECLARE cmd record;
BEGIN
  FOR cmd IN
    SELECT object_identity FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND schema_name = 'public'
  LOOP
    EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', cmd.object_identity);
  END LOOP;
END $$;
"""

# Event triggers normally need a superuser. Supabase's `postgres` role may not be allowed to
# create one; in that case skip it loudly instead of failing the whole migration (the CI job
# that asserts RLS on every table still catches a table that misses it).
CREATE_EVENT_TRIGGER = """
DO $$
BEGIN
  DROP EVENT TRIGGER IF EXISTS lineup_enable_rls;
  CREATE EVENT TRIGGER lineup_enable_rls ON ddl_command_end
    WHEN TAG IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
    EXECUTE FUNCTION public.lineup_enable_rls();
EXCEPTION WHEN insufficient_privilege THEN
  RAISE NOTICE 'Not allowed to create an event trigger here; skipped lineup_enable_rls';
END $$;
"""

CREATE_APP_ROLE = f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
    CREATE ROLE {APP_ROLE} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
      NOBYPASSRLS;
  END IF;
END $$;
"""


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    op.execute(ENABLE_RLS_ON_ALL_PUBLIC_TABLES)
    op.execute(REVOKE_FROM_SUPABASE_API_ROLES)
    op.execute(ENABLE_RLS_FUNCTION)
    op.execute(CREATE_EVENT_TRIGGER)

    op.execute(CREATE_APP_ROLE)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    for table in APP_TABLES:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.{table} TO {APP_ROLE}"
        )
        # Interim policy: RLS is on, and the API is the only client of these tables, so let
        # it through. #21 replaces this with team-scoped policies.
        op.execute(f"DROP POLICY IF EXISTS app_all ON public.{table}")
        op.execute(
            f"CREATE POLICY app_all ON public.{table} FOR ALL TO {APP_ROLE} "
            "USING (true) WITH CHECK (true)"
        )
    # Future tables get DML for the app automatically (RLS still denies until a policy exists).
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE}"
    )
    for table in APP_TABLES:
        op.execute(f"DROP POLICY IF EXISTS app_all ON public.{table}")
        op.execute(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON public.{table} FROM {APP_ROLE}"
        )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    # The role itself is kept: it may own a live login, and dropping a role that still has
    # privileges elsewhere fails.

    op.execute("DROP EVENT TRIGGER IF EXISTS lineup_enable_rls")
    op.execute("DROP FUNCTION IF EXISTS public.lineup_enable_rls()")
    # Supabase's own default (RLS off, Data API roles granted) is deliberately not restored:
    # that is the insecure state this migration exists to leave.
