"""Column types shared by the ORM models."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """A `timestamptz` column that always hands back timezone-aware UTC datetimes.

    Postgres stores an instant and returns it aware; SQLite has no such type and returns whatever
    text it stored, without a zone. This decorator makes both behave the same: a value going in
    must be aware (a naive one is a bug, so it raises instead of silently guessing a zone) and is
    converted to UTC; a value coming out is aware UTC. Application code can therefore compare
    and subtract datetimes without ever asking which database it runs on.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        """Convert an aware datetime to UTC; refuse a naive one."""
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "UtcDateTime needs a timezone-aware datetime, got a naive one"
            )
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        """Return the stored instant as aware UTC (SQLite drops the zone, so re-attach it)."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
