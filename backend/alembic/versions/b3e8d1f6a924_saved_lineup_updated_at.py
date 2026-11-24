"""saved_lineup_updated_at

#290. Adds `saved_lineups.updated_at` (timestamptz, NOT NULL, server default `now()`), the time
a lineup was last saved. Saved lineups can now be edited in place, and the value doubles as the
optimistic-concurrency token of `PUT /lineups/saved/{id}`: an edit carrying an older value is
refused with 409.

The column is added nullable, every existing row is backfilled with its own `created_at` (so a
never-edited lineup has both equal, the same as a new one), and only then made NOT NULL. The
table-level grants and RLS policy from `8b1f3c2d9a47` already cover a new column. The downgrade
drops the column; edits made in the meantime keep their new values, only the time is lost. A
timestamp is not personal data.

Revision ID: b3e8d1f6a924
Revises: e7a2c9b4d581
Create Date: 2026-11-24 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e8d1f6a924"
down_revision: str | Sequence[str] | None = "e7a2c9b4d581"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column, copy `created_at` into it, then make it NOT NULL with a default."""
    op.add_column(
        "saved_lineups",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE saved_lineups SET updated_at = created_at")
    with op.batch_alter_table("saved_lineups") as batch_op:
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        )


def downgrade() -> None:
    """Drop the column; nothing else depends on it."""
    with op.batch_alter_table("saved_lineups") as batch_op:
        batch_op.drop_column("updated_at")
