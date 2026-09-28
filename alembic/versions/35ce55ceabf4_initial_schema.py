"""initial_schema

Revision ID: 35ce55ceabf4
Revises:
Create Date: 2026-09-24 22:04:11.860337

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "35ce55ceabf4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "teams",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "players",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("nssz_number", sa.String(length=50), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "saved_lineups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_name", sa.String(length=120), nullable=False),
        sa.Column("opponent_name", sa.String(length=120), nullable=False),
        sa.Column("match_name", sa.String(length=200), nullable=False),
        sa.Column("division", sa.String(length=100), nullable=False),
        sa.Column("cap", sa.String(length=10), nullable=False),
        sa.Column("date", sa.String(length=50), nullable=False),
        sa.Column("coach", sa.String(length=200), nullable=False),
        sa.Column("doctor", sa.String(length=200), nullable=True),
        sa.Column("assistant_coach", sa.String(length=200), nullable=True),
        sa.Column("team_leader", sa.String(length=200), nullable=True),
        sa.Column("ball_thrower", sa.String(length=200), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("source_team_id", sa.UUID(), nullable=True),
        sa.Column("source_opponent_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["source_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_opponent_id"], ["teams.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lineup_player_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("saved_lineup_id", sa.UUID(), nullable=False),
        sa.Column("cap_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("nssz_number", sa.String(length=50), nullable=False),
        sa.Column("source_player_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["saved_lineup_id"], ["saved_lineups.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_player_id"], ["players.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("lineup_player_snapshots")
    op.drop_table("saved_lineups")
    op.drop_table("players")
    op.drop_table("teams")
