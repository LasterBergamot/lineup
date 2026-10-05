"""team_members_invitations_owner_not_null

Team collaboration groundwork (#19) and the owner-id cleanup that real sign-in needs (#52):

1. Rows created before sign-in existed have no owner (`teams.owner_id`, `players.user_id` and
   `saved_lineups.user_id` are NULL). They belong to nobody, so no signed-in user could ever see
   them again. This migration DELETES them (with everything that hangs off them) instead of
   assigning them to an arbitrary account. That is safe only because the sole database that
   ever held such rows is the dev project: there is no prod database yet, and a fresh
   database has none. Do not reuse this pattern for data that matters.
2. The three owner columns become NOT NULL.
3. `team_members` (who belongs to a team) and `team_invitations` (multi-use invite links, only
   the SHA-256 hash of the code is stored) are created. Every existing team gets its owner as
   an `owner` member.
4. Postgres only: both new tables get RLS, the interim `app_all` policy and DML for the
   `lineup_app` role, exactly like the earlier tables (a new table's migration must do this
   itself: RLS denies the app until a policy exists).

Revision ID: a3d5f7c91e26
Revises: c4e7a1b2d905
Create Date: 2026-10-05 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3d5f7c91e26"
down_revision: Union[str, Sequence[str], None] = "c4e7a1b2d905"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "lineup_app"
NEW_TABLES = ("team_members", "team_invitations")
ROLE_CHECK = "role IN ('owner', 'member')"


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def _delete_ownerless_rows() -> None:
    # Children before parents, so this also works where foreign keys are enforced.
    op.execute(
        "DELETE FROM lineup_player_snapshots WHERE saved_lineup_id IN "
        "(SELECT id FROM saved_lineups WHERE user_id IS NULL)"
    )
    op.execute("DELETE FROM saved_lineups WHERE user_id IS NULL")
    op.execute(
        "DELETE FROM players WHERE user_id IS NULL OR team_id IN "
        "(SELECT id FROM teams WHERE owner_id IS NULL)"
    )
    op.execute("DELETE FROM teams WHERE owner_id IS NULL")


def upgrade() -> None:
    _delete_ownerless_rows()

    for table, column in (
        ("teams", "owner_id"),
        ("players", "user_id"),
        ("saved_lineups", "user_id"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.UUID(), nullable=False)

    op.create_table(
        "team_members",
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(ROLE_CHECK, name="ck_team_members_role"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_id", "user_id"),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])

    op.create_table(
        "team_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column("invite_code_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(ROLE_CHECK, name="ck_team_invitations_role"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code_hash"),
    )
    op.create_index("ix_team_invitations_team_id", "team_invitations", ["team_id"])

    op.execute(
        "INSERT INTO team_members (team_id, user_id, role, joined_at) "
        "SELECT id, owner_id, 'owner', created_at FROM teams"
    )

    if _is_postgres():
        for table in NEW_TABLES:
            op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.{table} TO {APP_ROLE}"
            )
            op.execute(f"DROP POLICY IF EXISTS app_all ON public.{table}")
            op.execute(
                f"CREATE POLICY app_all ON public.{table} FOR ALL TO {APP_ROLE} "
                "USING (true) WITH CHECK (true)"
            )


def downgrade() -> None:
    # Dropping a table removes its policies and grants. The deleted ownerless rows are gone
    # for good; the owner columns just become nullable again.
    op.drop_index("ix_team_invitations_team_id", table_name="team_invitations")
    op.drop_table("team_invitations")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_table("team_members")

    for table, column in (
        ("saved_lineups", "user_id"),
        ("players", "user_id"),
        ("teams", "owner_id"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.alter_column(column, existing_type=sa.UUID(), nullable=True)
