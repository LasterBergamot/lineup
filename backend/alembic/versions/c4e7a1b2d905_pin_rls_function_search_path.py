"""pin_rls_function_search_path

Postgres only (a no-op on SQLite). Supabase's Security Advisor (lint 0011) flags
`public.lineup_enable_rls` because it had no fixed search_path. Its body only calls
pg_catalog functions (always searched) and uses the schema-qualified `object_identity`, so an
empty search_path is safe and stops a session from redirecting name lookups. This is a new
revision instead of an edit to `8b1f3c2d9a47`, which is already applied on the dev project.

Revision ID: c4e7a1b2d905
Revises: 8b1f3c2d9a47
Create Date: 2026-10-05 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4e7a1b2d905"
down_revision: Union[str, Sequence[str], None] = "8b1f3c2d9a47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alter_function(action: str) -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    op.execute(
        f"""
        DO $$
        BEGIN
          IF to_regprocedure('public.lineup_enable_rls()') IS NOT NULL THEN
            ALTER FUNCTION public.lineup_enable_rls() {action};
          END IF;
        END $$;
        """
    )


def upgrade() -> None:
    _alter_function("SET search_path = ''")


def downgrade() -> None:
    _alter_function("RESET search_path")
