"""snapshot_cap_unique_and_source_indexes

#64. Postgres does not index foreign keys on its own, so every `ON DELETE SET NULL` on the three
soft references scanned a whole table. Adds those indexes, and a unique index on
`(saved_lineup_id, cap_number)` so a cap number can only appear once per saved lineup even if
the API's own check is bypassed. A unique *index* rather than a constraint: it is the same
guarantee, and SQLite can create it without rebuilding the table.

Fails on a database that already holds a duplicate cap number in one lineup; the API has never
allowed that, so there should be none (check with `SELECT saved_lineup_id, cap_number, count(*)
FROM lineup_player_snapshots GROUP BY 1, 2 HAVING count(*) > 1`).

Revision ID: d9a4c6e81b32
Revises: b7d2e9a41c53
Create Date: 2026-11-01 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9a4c6e81b32"
down_revision: str | Sequence[str] | None = "b7d2e9a41c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the unique cap index and the three foreign-key indexes."""
    op.create_index(
        "ux_lineup_player_snapshots_lineup_cap",
        "lineup_player_snapshots",
        ["saved_lineup_id", "cap_number"],
        unique=True,
    )
    op.create_index(
        "ix_lineup_player_snapshots_source_player_id",
        "lineup_player_snapshots",
        ["source_player_id"],
    )
    op.create_index(
        "ix_saved_lineups_source_team_id", "saved_lineups", ["source_team_id"]
    )
    op.create_index(
        "ix_saved_lineups_source_opponent_id", "saved_lineups", ["source_opponent_id"]
    )


def downgrade() -> None:
    """Drop them again; no data is touched."""
    op.drop_index("ix_saved_lineups_source_opponent_id", table_name="saved_lineups")
    op.drop_index("ix_saved_lineups_source_team_id", table_name="saved_lineups")
    op.drop_index(
        "ix_lineup_player_snapshots_source_player_id",
        table_name="lineup_player_snapshots",
    )
    op.drop_index(
        "ux_lineup_player_snapshots_lineup_cap", table_name="lineup_player_snapshots"
    )
