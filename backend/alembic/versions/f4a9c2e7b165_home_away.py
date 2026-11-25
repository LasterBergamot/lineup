"""home_away

#296. Adds two nullable columns: `saved_lineups.is_home` (BOOLEAN, true = home, false = away,
NULL = unknown) and `teams.home_venue` (VARCHAR 200, the venue the lineup creator pre-fills as
the location of a home lineup). Existing rows keep NULL in both: old lineups have no recorded
side and old teams no venue. Neither is personal data.

Revision ID: f4a9c2e7b165
Revises: b3e8d1f6a924
Create Date: 2026-11-24 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a9c2e7b165"
down_revision: str | Sequence[str] | None = "b3e8d1f6a924"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable `saved_lineups.is_home` and `teams.home_venue` columns."""
    op.add_column("saved_lineups", sa.Column("is_home", sa.Boolean(), nullable=True))
    op.add_column(
        "teams", sa.Column("home_venue", sa.String(length=200), nullable=True)
    )


def downgrade() -> None:
    """Drop both columns; the recorded sides and venues are lost, nothing else is touched."""
    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_column("home_venue")
    with op.batch_alter_table("saved_lineups") as batch_op:
        batch_op.drop_column("is_home")
