"""member_display_name

`team_members.display_name` (#245): the member's name, copied from their own verified token when
they create or join a team and refreshed whenever they list their teams. The Members page shows it
so owners can tell members apart. Nullable: existing members have no name until they next open
the app, and a token may carry none. It is deleted with the membership row. The table-level
grants and RLS policy from `a3d5f7c91e26` already cover a new column.

Revision ID: a9e3c7d51f28
Revises: f2c8a5d7e931
Create Date: 2026-11-01 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9e3c7d51f28"
down_revision: str | Sequence[str] | None = "f2c8a5d7e931"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable member display name."""
    op.add_column(
        "team_members",
        sa.Column("display_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    """Drop it again (the names are lost; the memberships stay)."""
    op.drop_column("team_members", "display_name")
