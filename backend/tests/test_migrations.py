"""The data-changing migrations `a3d5f7c91e26` and `e5b8c2d41f70`, run for real against a
throw-away SQLite file.

Schema drift is checked by `task migrate-check`; this proves what happens to *existing rows*:
ownerless pre-auth rows are removed, owned rows survive, every team gets its owner as a member,
and saved lineups move into a workspace team.
"""

import os
import sqlite3
from contextlib import closing
import subprocess
import sys
import uuid

import pytest

BEFORE = "c4e7a1b2d905"
AFTER_OWNERS = "a3d5f7c91e26"
AFTER_WORKSPACE = "e5b8c2d41f70"


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

    alembic(database, "upgrade", AFTER_OWNERS)

    assert _count(database, "SELECT count(*) FROM teams") == 1
    assert _count(database, "SELECT count(*) FROM teams WHERE name = 'Owned'") == 1
    # p_orphan (no user) and p_in_orphan (on the removed team) are gone
    assert _count(database, "SELECT count(*) FROM players") == 1
    assert _count(database, "SELECT count(*) FROM saved_lineups") == 1
    assert _count(database, "SELECT count(*) FROM lineup_player_snapshots") == 1


def test_every_remaining_team_gets_its_owner_as_a_member(database):
    owner = _id()
    _seed(database, owner)

    alembic(database, "upgrade", AFTER_OWNERS)

    with closing(sqlite3.connect(database)) as db:
        rows = db.execute("SELECT user_id, role FROM team_members").fetchall()
    assert rows == [(owner, "owner")]


def test_owner_columns_are_not_null_afterwards(database):
    alembic(database, "upgrade", AFTER_OWNERS)
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


# ── e5b8c2d41f70: teams become workspaces ───────────────────────────────────


def _seed_workspace_data(path):
    """State right after a3d5f7c91e26: users U (team T) and V (no team), and W's team T2."""
    ids = {k: _id() for k in ("U", "V", "W", "T", "T2")}
    ids.update({k: _id() for k in ("p_ok", "p_teamless")})
    ids.update({k: _id() for k in ("l_src", "l_nosrc", "l_foreign", "l_homeless")})
    ids.update({k: _id() for k in ("s_src", "s_nosrc", "s_foreign", "s_homeless")})
    now = "2026-10-01 10:00:00"
    with closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        for team, owner in (("T", "U"), ("T2", "W")):
            db.execute(
                "INSERT INTO teams VALUES (?, ?, ?, 1, ?)",
                (ids[team], team, ids[owner], now),
            )
            db.execute(
                "INSERT INTO team_members VALUES (?, ?, 'owner', ?)",
                (ids[team], ids[owner], now),
            )
        for pid, team in (("p_ok", ids["T"]), ("p_teamless", None)):
            db.execute(
                "INSERT INTO players VALUES (?, 'P', 'N', ?, ?, ?)",
                (ids[pid], team, ids["U"], now),
            )
        # (lineup, creator, source team)
        for lid, creator, source in (
            ("l_src", "U", ids["T"]),
            ("l_nosrc", "U", None),
            ("l_foreign", "U", ids["T2"]),  # U is not a member of T2
            ("l_homeless", "V", None),  # V belongs to no team at all
        ):
            db.execute(
                "INSERT INTO saved_lineups VALUES "
                "(?, 'A', 'B', 'A - B', 'D', 'Fehér', 'd', 'c', NULL, NULL, NULL, NULL, "
                "?, ?, ?, NULL)",
                (ids[lid], ids[creator], now, source),
            )
            db.execute(
                "INSERT INTO lineup_player_snapshots VALUES (?, ?, 1, 'P', 'N', NULL)",
                (_id(), ids[lid]),
            )
        db.commit()
    return ids


@pytest.fixture
def workspace_database(database):
    alembic(database, "upgrade", AFTER_OWNERS)
    return database, _seed_workspace_data(database)


def test_lineups_move_into_a_team_their_creator_belongs_to(workspace_database):
    database, ids = workspace_database
    alembic(database, "upgrade", AFTER_WORKSPACE)
    with closing(sqlite3.connect(database)) as db:
        placed = dict(db.execute("SELECT id, team_id FROM saved_lineups").fetchall())
    assert placed == {
        ids["l_src"]: ids["T"],  # made for T, creator is a member: stays there
        ids["l_nosrc"]: ids["T"],  # no source: the creator's first team
        ids["l_foreign"]: ids["T"],  # source T2 is not theirs: the creator's first team
    }  # l_homeless (creator has no team) is gone
    assert _count(database, "SELECT count(*) FROM lineup_player_snapshots") == 3


def test_teamless_players_are_removed_and_the_rest_keep_their_team(workspace_database):
    database, ids = workspace_database
    alembic(database, "upgrade", AFTER_WORKSPACE)
    with closing(sqlite3.connect(database)) as db:
        rows = db.execute("SELECT id, team_id, created_by FROM players").fetchall()
    assert rows == [(ids["p_ok"], ids["T"], ids["U"])]


def test_columns_are_renamed_and_required_and_indexed(workspace_database):
    database, _ = workspace_database
    alembic(database, "upgrade", AFTER_WORKSPACE)
    with closing(sqlite3.connect(database)) as db:
        teams = {r[1] for r in db.execute("PRAGMA table_info(teams)")}
        players = {r[1]: r[3] for r in db.execute("PRAGMA table_info(players)")}
        lineups = {r[1]: r[3] for r in db.execute("PRAGMA table_info(saved_lineups)")}
        fks = db.execute("PRAGMA foreign_key_list(saved_lineups)").fetchall()
        indexes = {
            r[1] for r in db.execute("SELECT * FROM sqlite_master WHERE type='index'")
        }
    assert "created_by" in teams and "owner_id" not in teams
    assert players["created_by"] == 1 and players["team_id"] == 1
    assert lineups["created_by"] == 1 and lineups["team_id"] == 1
    assert "user_id" not in players and "user_id" not in lineups
    assert any(
        fk[2] == "teams" and fk[3] == "team_id" and fk[6] == "RESTRICT" for fk in fks
    )
    assert {"ix_players_team_id", "ix_saved_lineups_team_id"} <= indexes


def test_the_workspace_migration_can_be_undone(workspace_database):
    database, _ = workspace_database
    alembic(database, "upgrade", AFTER_WORKSPACE)
    alembic(database, "downgrade", AFTER_OWNERS)
    with closing(sqlite3.connect(database)) as db:
        teams = {r[1] for r in db.execute("PRAGMA table_info(teams)")}
        lineups = {r[1] for r in db.execute("PRAGMA table_info(saved_lineups)")}
    assert "owner_id" in teams
    assert "user_id" in lineups and "team_id" not in lineups
