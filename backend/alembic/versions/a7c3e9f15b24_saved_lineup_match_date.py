"""saved_lineup_match_date

#287. Adds the nullable `saved_lineups.match_date` (DATE) and `match_time` (TIME), the match
date stored structured so saved lineups can be filtered by date range (#295). The printed
`saved_lineups.date` text stays and is still what the document shows.

Backfill: a legacy `date` that looks like `YYYY. MM. DD.` or `YYYY. MM. DD. HH:MM` (and is a real
calendar date and time) fills the two new columns. Anything else, free text such as "2024.
december 21.", is left NULL: the text is kept, the lineup just cannot be found by a date filter.
The downgrade drops the columns; the printed text is untouched. The match date is not personal data.

Revision ID: a7c3e9f15b24
Revises: d1b6e4a97c53
Create Date: 2026-11-24 15:00:00.000000

"""

import re
from collections.abc import Sequence
from datetime import date, time

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e9f15b24"
down_revision: str | Sequence[str] | None = "d1b6e4a97c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRINTED = re.compile(r"(\d{4})\. (\d{1,2})\. (\d{1,2})\.(?: (\d{1,2}):(\d{2}))?")


def parse_printed_date(text: str) -> tuple[date, time | None] | None:
    """Parse `YYYY. MM. DD.[ HH:MM]`; return None for anything else or an impossible date."""
    found = _PRINTED.fullmatch(text.strip())
    if found is None:
        return None
    year, month, day, hour, minute = found.groups()
    try:
        parsed_date = date(int(year), int(month), int(day))
        parsed_time = time(int(hour), int(minute)) if hour is not None else None
    except ValueError:
        return None
    return parsed_date, parsed_time


def upgrade() -> None:
    """Add the two columns and backfill them from the printed text where it parses."""
    op.add_column("saved_lineups", sa.Column("match_date", sa.Date(), nullable=True))
    op.add_column("saved_lineups", sa.Column("match_time", sa.Time(), nullable=True))

    lineups = sa.table(
        "saved_lineups",
        sa.column("id", sa.Uuid()),
        sa.column("date", sa.String()),
        sa.column("match_date", sa.Date()),
        sa.column("match_time", sa.Time()),
    )
    bind = op.get_bind()
    for row_id, text in bind.execute(sa.select(lineups.c.id, lineups.c.date)).all():
        parsed = parse_printed_date(text)
        if parsed is not None:
            bind.execute(
                lineups.update()
                .where(lineups.c.id == row_id)
                .values(match_date=parsed[0], match_time=parsed[1])
            )


def downgrade() -> None:
    """Drop the structured columns; the printed `date` text is untouched."""
    with op.batch_alter_table("saved_lineups") as batch_op:
        batch_op.drop_column("match_time")
        batch_op.drop_column("match_date")
