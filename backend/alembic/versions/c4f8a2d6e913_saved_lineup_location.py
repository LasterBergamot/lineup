"""saved_lineup_location

#294. Adds the nullable `saved_lineups.location` (VARCHAR 200), the venue of a match, so the
history can show it and (#295) search by it. It is never printed: the official sheet has no
venue. Existing lineups stay NULL. The downgrade drops the column. A venue is not personal data.

Revision ID: c4f8a2d6e913
Revises: a7c3e9f15b24
Create Date: 2026-11-24 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f8a2d6e913"
down_revision: str | Sequence[str] | None = "a7c3e9f15b24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable `location` column."""
    op.add_column(
        "saved_lineups", sa.Column("location", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    """Drop the column; nothing else depends on it."""
    with op.batch_alter_table("saved_lineups") as batch_op:
        batch_op.drop_column("location")
