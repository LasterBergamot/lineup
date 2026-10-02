from datetime import datetime, timezone

import pytest

from lineup.db.models import Player, SavedLineup, Team, _utcnow


def test_utcnow_is_naive_utc():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    value = _utcnow()
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    assert value.tzinfo is None
    assert before <= value <= after


@pytest.mark.parametrize("model", [Team, Player, SavedLineup])
def test_created_at_default_is_naive(model):
    # Postgres (asyncpg) rejects an aware datetime for a TIMESTAMP WITHOUT TIME ZONE
    # column; SQLite hides the problem by dropping tzinfo, so assert it directly.
    default = model.__table__.c.created_at.default

    assert default.arg(None).tzinfo is None
