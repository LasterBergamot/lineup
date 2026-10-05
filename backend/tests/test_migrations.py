"""The data-changing migration `a3d5f7c91e26`, run for real against a throw-away SQLite file.

Schema drift is checked by `task migrate-check`; this proves what happens to *existing rows*:
ownerless pre-auth rows are removed, owned rows survive, and every team gets its owner as a
member.
"""

import os
import sqlite3
from contextlib import closing
import subprocess
import sys
import uuid

import pytest

BEFORE = "c4e7a1b2d905"


def alembic(db_path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *args],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
            "MIGRATE_DATABASE_URL": "",
        },
    )


def _id() -> str:
    return uuid.uuid4().hex


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "migrate.db"
    alembic(path, "upgrade", BEFORE)
    return path


def _seed(path, owner: str):
    """Two teams (one owned, one not), players and lineups on both sides."""
    ids = {k: _id() for k in ("t_own", "t_orphan", "p_own", "p_orphan", "p_in_orphan")}
    ids.update({k: _id() for k in ("l_own", "l_orphan", "s_own", "s_orphan")})
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        now = "2026-10-01 10:00:00"
        db.execute(
            "INSERT INTO teams VALUES (?, 'Owned', ?, 1, ?)", (ids["t_own"], owner, now)
        )
        db.execute(
            "INSERT INTO teams VALUES (?, 'Orphan', NULL, 1, ?)", (ids["t_orphan"], now)
        )
        for pid, team, user in (
            ("p_own", "t_own", owner),
            ("p_orphan", "t_own", None),
            ("p_in_orphan", "t_orphan", owner),
        ):
            db.execute(
                "INSERT INTO players VALUES (?, 'P', 'N', ?, ?, ?)",
                (ids[pid], ids[team], user, now),
            )
        for lid, user in (("l_own", owner), ("l_orphan", None)):
            db.execute(
                "INSERT INTO saved_lineups VALUES "
                "(?, 'A', 'B', 'A - B', 'D', 'Fehér', 'd', 'c', NULL, NULL, NULL, NULL, "
                "?, ?, NULL, NULL)",
                (ids[lid], user, now),
            )
        for sid, lid in (("s_own", "l_own"), ("s_orphan", "l_orphan")):
            db.execute(
                "INSERT INTO lineup_player_snapshots VALUES (?, ?, 1, 'P', 'N', NULL)",
                (ids[sid], ids[lid]),
            )
        db.commit()
    return ids


def _count(path, sql: str) -> int:
    with closing(sqlite3.connect(path)) as db:
        return db.execute(sql).fetchone()[0]


def test_ownerless_rows_are_removed_and_owned_rows_survive(database):
    owner = _id()
    _seed(database, owner)

    alembic(database, "upgrade", "head")

    assert _count(database, "SELECT count(*) FROM teams") == 1
    assert _count(database, "SELECT count(*) FROM teams WHERE name = 'Owned'") == 1
    # p_orphan (no user) and p_in_orphan (on the removed team) are gone
    assert _count(database, "SELECT count(*) FROM players") == 1
    assert _count(database, "SELECT count(*) FROM saved_lineups") == 1
    assert _count(database, "SELECT count(*) FROM lineup_player_snapshots") == 1


def test_every_remaining_team_gets_its_owner_as_a_member(database):
    owner = _id()
    _seed(database, owner)

    alembic(database, "upgrade", "head")

    with closing(sqlite3.connect(database)) as db:
        rows = db.execute("SELECT user_id, role FROM team_members").fetchall()
    assert rows == [(owner, "owner")]


def test_owner_columns_are_not_null_afterwards(database):
    alembic(database, "upgrade", "head")
    with closing(sqlite3.connect(database)) as db:
        for table, column in (
            ("teams", "owner_id"),
            ("players", "user_id"),
            ("saved_lineups", "user_id"),
        ):
            info = {r[1]: r[3] for r in db.execute(f"PRAGMA table_info({table})")}
            assert info[column] == 1, f"{table}.{column} should be NOT NULL"


def test_an_empty_database_migrates_up_and_back_down(database):
    alembic(database, "upgrade", "head")
    alembic(database, "downgrade", BEFORE)
    with closing(sqlite3.connect(database)) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master")}
        info = {r[1]: r[3] for r in db.execute("PRAGMA table_info(teams)")}
    assert "team_members" not in tables
    assert info["owner_id"] == 0
