"""team_as_workspace

Teams become workspaces (#49): everything a club owns belongs to a team and every member of
that team may use it.

1. `teams.owner_id`, `players.user_id` and `saved_lineups.user_id` are renamed to `created_by`.
   They were the access key; from now on access comes from `team_members` and these columns
   only record who created a row.
2. `players.team_id` becomes NOT NULL. Players without a team have no workspace and nobody could
   reach them any more, so they are DELETED (they can only exist on the dev database).
3. `saved_lineups.team_id` (the workspace) is added, NOT NULL, with `ON DELETE RESTRICT`.
   Existing lineups are moved into the team they were made for (`source_team_id`) when their
   creator is a member of it, otherwise into the creator's oldest team. A lineup whose creator
   belongs to no team is DELETED with its snapshots.
4. Indexes on both `team_id` columns, because every access check now joins on them.

Revision ID: e5b8c2d41f70
Revises: a3d5f7c91e26
Create Date: 2026-10-05 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5b8c2d41f70"
down_revision: Union[str, Sequence[str], None] = "a3d5f7c91e26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MOVE_TO_CREATORS_FIRST_TEAM = (
    "UPDATE saved_lineups SET team_id = ("
    "SELECT tm.team_id FROM team_members tm WHERE tm.user_id = saved_lineups.created_by "
    "ORDER BY tm.joined_at, tm.team_id LIMIT 1) WHERE team_id IS NULL"
)


def upgrade() -> None:
    with op.batch_alter_table("teams") as batch:
        batch.alter_column("owner_id", new_column_name="created_by")

    op.execute("DELETE FROM players WHERE team_id IS NULL")
    with op.batch_alter_table("players") as batch:
        batch.alter_column("user_id", new_column_name="created_by")
        batch.alter_column("team_id", existing_type=sa.UUID(), nullable=False)
        batch.create_index("ix_players_team_id", ["team_id"])

    with op.batch_alter_table("saved_lineups") as batch:
        batch.alter_column("user_id", new_column_name="created_by")
        batch.add_column(sa.Column("team_id", sa.UUID(), nullable=True))

    op.execute(
        "UPDATE saved_lineups SET team_id = source_team_id WHERE EXISTS "
        "(SELECT 1 FROM team_members tm WHERE tm.team_id = saved_lineups.source_team_id "
        "AND tm.user_id = saved_lineups.created_by)"
    )
    op.execute(MOVE_TO_CREATORS_FIRST_TEAM)
    op.execute(
        "DELETE FROM lineup_player_snapshots WHERE saved_lineup_id IN "
        "(SELECT id FROM saved_lineups WHERE team_id IS NULL)"
    )
    op.execute("DELETE FROM saved_lineups WHERE team_id IS NULL")

    with op.batch_alter_table("saved_lineups") as batch:
        batch.alter_column("team_id", existing_type=sa.UUID(), nullable=False)
        batch.create_foreign_key(
            "fk_saved_lineups_team_id_teams",
            "teams",
            ["team_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_saved_lineups_team_id", ["team_id"])


def downgrade() -> None:
    with op.batch_alter_table("saved_lineups") as batch:
        batch.drop_index("ix_saved_lineups_team_id")
        batch.drop_constraint("fk_saved_lineups_team_id_teams", type_="foreignkey")
        batch.drop_column("team_id")
        batch.alter_column("created_by", new_column_name="user_id")

    with op.batch_alter_table("players") as batch:
        batch.drop_index("ix_players_team_id")
        batch.alter_column("team_id", existing_type=sa.UUID(), nullable=True)
        batch.alter_column("created_by", new_column_name="user_id")

    with op.batch_alter_table("teams") as batch:
        batch.alter_column("created_by", new_column_name="owner_id")
