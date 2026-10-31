"""invitation_inviter_name

`team_invitations.invited_by_name` (#51): the inviter's display name, copied from their verified
token when the link is created. The public invite preview shows it ("X invited you to Y") without
looking anything up, and it is deleted with the invitation row. Nullable: the token may carry no
name. The table-level grants and RLS policy from `a3d5f7c91e26` already cover a new column.

Revision ID: b7d2e9a41c53
Revises: e5b8c2d41f70
Create Date: 2026-10-31 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d2e9a41c53"
down_revision: str | Sequence[str] | None = "e5b8c2d41f70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable inviter display name."""
    op.add_column(
        "team_invitations",
        sa.Column("invited_by_name", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    """Drop it again (the names are lost; the links keep working)."""
    op.drop_column("team_invitations", "invited_by_name")
