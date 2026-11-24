"""players_unique_nssz_per_team

#284. The NSSZ (federation licence) number identifies a person, so one team's roster must not hold
it twice. Adds the unique expression index `ux_players_team_nssz` on `(team_id,
lower(nssz_number))`: case-insensitive, team-scoped, and valid on SQLite and Postgres. The API
checks first and answers 409; the index is what stops two concurrent requests. (The API trims
the number on the way in; the index does not, so it only ever sees trimmed values.)

The upgrade first looks for existing duplicates and, if there are any, stops with a message
instead of letting the index creation fail with a bare constraint error. It deliberately does not
delete anything: which of two roster entries is the right one is a human decision. The message
holds counts and team ids only, never names or NSSZ numbers (personal data must not reach a
migration log). To list the offenders yourself, run, with the team id from the message:

    SELECT id, name, nssz_number FROM players WHERE team_id = '<team id>'
    ORDER BY lower(nssz_number), created_at;

then delete or correct the extra entries (saved lineups keep their own copy, so deleting a roster
player never changes a lineup) and run the upgrade again.

Revision ID: c8f3a1d6e472
Revises: a9e3c7d51f28
Create Date: 2026-11-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8f3a1d6e472"
down_revision: str | Sequence[str] | None = "a9e3c7d51f28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ux_players_team_nssz"


def upgrade() -> None:
    """Refuse to continue while a team has the same NSSZ number twice, then create the index."""
    duplicated_teams = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT team_id, count(*) FROM players "
                "GROUP BY team_id, lower(nssz_number) HAVING count(*) > 1"
            )
        )
        .fetchall()
    )
    if duplicated_teams:
        teams = sorted({str(row[0]) for row in duplicated_teams})
        raise RuntimeError(
            f"{len(duplicated_teams)} NSSZ number(s) appear more than once on the roster of "
            f"{len(teams)} team(s) (team ids: {', '.join(teams)}). Remove or correct the "
            "duplicates, then run the migration again; see the docstring of "
            "alembic/versions/c8f3a1d6e472_players_unique_nssz_per_team.py for the query."
        )
    op.create_index(
        INDEX_NAME,
        "players",
        ["team_id", sa.text("lower(nssz_number)")],
        unique=True,
    )


def downgrade() -> None:
    """Drop the index; no data is touched."""
    op.drop_index(INDEX_NAME, table_name="players")
