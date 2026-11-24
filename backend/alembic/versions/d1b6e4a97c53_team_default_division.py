"""team_default_division

#288. Adds the nullable `teams.division` (`String(100)`): the division a team normally plays in
(for example "OB II."), which the lineup creator pre-fills. Nullable with no default, so existing
teams simply have none. It is a team attribute, not personal data. Saved lineups keep their own
copy in `saved_lineups.division`, so changing the team's value never edits a lineup.

Revision ID: d1b6e4a97c53
Revises: c8f3a1d6e472
Create Date: 2026-11-24 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1b6e4a97c53"
down_revision: str | Sequence[str] | None = "c8f3a1d6e472"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable `teams.division` column."""
    op.add_column("teams", sa.Column("division", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Drop `teams.division`; the default divisions are lost, lineups are untouched."""
    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_column("division")
