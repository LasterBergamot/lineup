"""timestamptz_and_server_defaults

#65. Postgres only (a no-op on SQLite, which has no timestamptz and, on a migrated file, keeps
the Python-side defaults).

1. Every timestamp column becomes `timestamptz`. The old `timestamp without time zone` columns
   held naive UTC (the app stripped the zone before writing), so the conversion is
   `AT TIME ZONE 'UTC'`: no value changes, it only gains its zone. The ORM type that goes with
   it is `lineup.db.types.UtcDateTime`.
2. `is_public`, both `role` columns and every `created_at` / `joined_at` get a *server* default,
   so a row inserted outside the app (Supabase Studio, a manual `INSERT`) no longer fails on a
   NOT NULL column it never heard of.

Revision ID: f2c8a5d7e931
Revises: d9a4c6e81b32
Create Date: 2026-11-01 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2c8a5d7e931"
down_revision: str | Sequence[str] | None = "d9a4c6e81b32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column) of every timestamp that becomes timestamptz.
TIMESTAMPS = (
    ("teams", "created_at"),
    ("players", "created_at"),
    ("saved_lineups", "created_at"),
    ("team_members", "joined_at"),
    ("team_invitations", "created_at"),
    ("team_invitations", "expires_at"),
    ("team_invitations", "revoked_at"),
)
# The subset that also defaults to "now".
NOW_DEFAULTS = tuple(c for c in TIMESTAMPS if c[1] not in {"expires_at", "revoked_at"})
ROLE_TABLES = ("team_members", "team_invitations")


def upgrade() -> None:
    """Convert the timestamps to timestamptz and add the server defaults (Postgres only)."""
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, column in TIMESTAMPS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
    for table, column in NOW_DEFAULTS:
        op.alter_column(table, column, server_default=sa.func.now())
    op.alter_column("teams", "is_public", server_default=sa.true())
    for table in ROLE_TABLES:
        op.alter_column(table, "role", server_default=sa.text("'member'"))


def downgrade() -> None:
    """Drop the defaults and convert back to naive UTC (Postgres only)."""
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ROLE_TABLES:
        op.alter_column(table, "role", server_default=None)
    op.alter_column("teams", "is_public", server_default=None)
    for table, column in NOW_DEFAULTS:
        op.alter_column(table, column, server_default=None)
    for table, column in TIMESTAMPS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
