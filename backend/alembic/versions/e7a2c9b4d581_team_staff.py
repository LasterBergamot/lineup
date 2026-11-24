"""team_staff

#292. Adds `team_staff`: the coach, assistant coach, team leader and ball thrower a team keeps so
they need not be retyped for every lineup. A name per row, nothing else (no phone, e-mail or
licence). `source_player_id` remembers the roster player an entry was picked from
(`ON DELETE SET NULL`: the name is a copy and survives the player). The partial unique index
`ux_team_staff_default_role` allows at most one default per team and role. Rows go with their
team (`ON DELETE CASCADE`). Existing data is untouched: the table starts empty.

Postgres only: like every earlier table, the new one gets RLS, the interim `app_all` policy and
DML for the `lineup_app` role (RLS denies the app until a policy exists).

Revision ID: e7a2c9b4d581
Revises: c4f8a2d6e913
Create Date: 2026-11-24 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a2c9b4d581"
down_revision: str | Sequence[str] | None = "c4f8a2d6e913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "lineup_app"
ROLE_CHECK = "role IN ('coach', 'assistant_coach', 'team_leader', 'ball_thrower')"


def upgrade() -> None:
    """Create the table, its indexes and (on Postgres) its RLS policy and grant."""
    op.create_table(
        "team_staff",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("team_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_player_id", sa.UUID(), nullable=True),
        sa.Column(
            "is_default", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(ROLE_CHECK, name="ck_team_staff_role"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_player_id"], ["players.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_staff_team_id", "team_staff", ["team_id"])
    op.create_index(
        "ix_team_staff_source_player_id", "team_staff", ["source_player_id"]
    )
    op.create_index(
        "ux_team_staff_default_role",
        "team_staff",
        ["team_id", "role"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default"),
    )

    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE public.team_staff ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.team_staff TO {APP_ROLE}"
        )
        op.execute("DROP POLICY IF EXISTS app_all ON public.team_staff")
        op.execute(
            f"CREATE POLICY app_all ON public.team_staff FOR ALL TO {APP_ROLE} "
            "USING (true) WITH CHECK (true)"
        )


def downgrade() -> None:
    """Drop the table; its indexes, policy and grant go with it. The staff names are gone."""
    op.drop_index("ux_team_staff_default_role", table_name="team_staff")
    op.drop_index("ix_team_staff_source_player_id", table_name="team_staff")
    op.drop_index("ix_team_staff_team_id", table_name="team_staff")
    op.drop_table("team_staff")
