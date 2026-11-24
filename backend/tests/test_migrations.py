"""The data-changing migrations (`a3d5f7c91e26`, `e5b8c2d41f70`, `c8f3a1d6e472`, `d1b6e4a97c53` and
later ones, each in its own section below), run for real against a
throw-away SQLite file.

Schema drift is checked by `task migrate-check`; this proves what happens to *existing rows*:
ownerless pre-auth rows are removed, owned rows survive, every team gets its owner as a member,
and saved lineups move into a workspace team.
"""

import os
import sqlite3
import subprocess
import sys
import uuid
from contextlib import closing

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


# --- c8f3a1d6e472: unique NSSZ number per team (#284) -----------------------------------------

BEFORE_NSSZ = "a9e3c7d51f28"
AFTER_NSSZ = "c8f3a1d6e472"


@pytest.fixture
def roster_database(tmp_path):
    path = tmp_path / "roster.db"
    alembic(path, "upgrade", BEFORE_NSSZ)
    return path


def _seed_roster(path, players: list[tuple[str, str]]) -> dict[str, str]:
    """One user, two teams ('A', 'B'); `players` are (team key, NSSZ number) pairs."""
    ids = {"U": _id(), "A": _id(), "B": _id()}
    now = "2026-11-01 10:00:00"
    with closing(sqlite3.connect(path)) as db:
        for team in ("A", "B"):
            db.execute(
                "INSERT INTO teams VALUES (?, ?, ?, 1, ?)",
                (ids[team], team, ids["U"], now),
            )
        for team, number in players:
            db.execute(
                "INSERT INTO players VALUES (?, 'Name', ?, ?, ?, ?)",
                (_id(), number, ids[team], ids["U"], now),
            )
        db.commit()
    return ids


def _indexes(path) -> set[str]:
    with closing(sqlite3.connect(path)) as db:
        return {
            r[1] for r in db.execute("SELECT * FROM sqlite_master WHERE type='index'")
        }


def test_a_clean_roster_gets_the_unique_index_and_it_is_enforced(roster_database):
    ids = _seed_roster(roster_database, [("A", "N1"), ("B", "N1"), ("A", "N2")])
    alembic(roster_database, "upgrade", AFTER_NSSZ)
    assert "ux_players_team_nssz" in _indexes(roster_database)
    assert (
        _count(roster_database, "SELECT count(*) FROM players") == 3
    )  # nothing deleted
    with (
        closing(sqlite3.connect(roster_database)) as db,
        pytest.raises(sqlite3.IntegrityError),
    ):
        db.execute(
            "INSERT INTO players VALUES (?, 'X', 'n1', ?, ?, '2026-11-01 10:00:00')",
            (_id(), ids["A"], ids["U"]),
        )


def test_existing_duplicates_stop_the_upgrade_without_leaking_numbers(roster_database):
    ids = _seed_roster(
        roster_database, [("A", "SECRET-7"), ("A", "secret-7"), ("B", "SECRET-7")]
    )
    with pytest.raises(subprocess.CalledProcessError) as failure:
        alembic(roster_database, "upgrade", AFTER_NSSZ)
    output = failure.value.stderr.decode()
    assert "appear more than once" in output
    assert ids["A"] in output and ids["B"] not in output
    assert "SECRET" not in output.upper()
    assert "ux_players_team_nssz" not in _indexes(roster_database)
    assert (
        _count(roster_database, "SELECT count(*) FROM players") == 3
    )  # nothing deleted


def test_the_nssz_migration_can_be_undone(roster_database):
    _seed_roster(roster_database, [("A", "N1")])
    alembic(roster_database, "upgrade", AFTER_NSSZ)
    alembic(roster_database, "downgrade", BEFORE_NSSZ)
    assert "ux_players_team_nssz" not in _indexes(roster_database)
    assert _count(roster_database, "SELECT count(*) FROM players") == 1
    # and the duplicates it used to forbid are allowed again
    with closing(sqlite3.connect(roster_database)) as db:
        team, user = db.execute("SELECT team_id, created_by FROM players").fetchone()
        db.execute(
            "INSERT INTO players VALUES (?, 'X', 'N1', ?, ?, '2026-11-01 10:00:00')",
            (_id(), team, user),
        )
        db.commit()


# --- d1b6e4a97c53: default division per team (#288) -------------------------------------------

AFTER_DIVISION = "d1b6e4a97c53"


def _team_columns(path) -> set[str]:
    with closing(sqlite3.connect(path)) as db:
        return {r[1] for r in db.execute("PRAGMA table_info(teams)")}


def test_the_division_column_is_added_empty_and_removed_again(roster_database):
    ids = _seed_roster(roster_database, [])
    alembic(roster_database, "upgrade", AFTER_NSSZ)
    assert "division" not in _team_columns(roster_database)
    alembic(roster_database, "upgrade", AFTER_DIVISION)
    assert "division" in _team_columns(roster_database)
    with closing(sqlite3.connect(roster_database)) as db:
        divisions = [r[0] for r in db.execute("SELECT division FROM teams")]
        assert divisions == [None, None]  # existing teams have no default
        db.execute("UPDATE teams SET division = 'OB II.' WHERE id = ?", (ids["A"],))
        db.commit()
    alembic(roster_database, "downgrade", AFTER_NSSZ)
    assert "division" not in _team_columns(roster_database)
    assert _count(roster_database, "SELECT count(*) FROM teams") == 2


# --- a7c3e9f15b24: structured match date (#287) ------------------------------------------------

AFTER_MATCH_DATE = "a7c3e9f15b24"

LEGACY_DATES = {
    "plain": ("2024. 12. 21.", "2024-12-21", None),
    "timed": ("2026. 11. 24. 18:30", "2026-11-24", "18:30:00.000000"),
    "unpadded": ("2025. 3. 9.", "2025-03-09", None),
    "words": ("2024. december 21.", None, None),
    "empty": ("", None, None),
    "impossible_day": ("2025. 02. 30.", None, None),
    "impossible_time": ("2025. 02. 20. 25:61", None, None),
    "extra_text": ("2024. 12. 21. Szeged", None, None),
}


def _seed_dated_lineups(path) -> dict[str, str]:
    ids = {key: _id() for key in LEGACY_DATES}
    with closing(sqlite3.connect(path)) as db:
        for key, (text, _, _) in LEGACY_DATES.items():
            db.execute(
                "INSERT INTO saved_lineups (id, team_id, team_name, opponent_name, "
                "match_name, division, cap, date, coach, created_by, created_at) "
                "VALUES (?, ?, 'A', 'B', 'A - B', 'D', 'Fehér', ?, 'c', ?, "
                "'2026-11-01 10:00:00')",
                (ids[key], _id(), text, _id()),
            )
        db.commit()
    return ids


def test_match_date_is_backfilled_from_parseable_text_only(roster_database):
    ids = _seed_dated_lineups(roster_database)
    alembic(roster_database, "upgrade", AFTER_DIVISION)
    alembic(roster_database, "upgrade", AFTER_MATCH_DATE)
    with closing(sqlite3.connect(roster_database)) as db:
        rows = {
            r[0]: r[1:]
            for r in db.execute(
                "SELECT id, date, match_date, match_time FROM saved_lineups"
            )
        }
    for key, (text, match_date, match_time) in LEGACY_DATES.items():
        # the printed text is never touched; unparseable rows stay NULL
        assert rows[ids[key]] == (text, match_date, match_time), key


def test_the_match_date_migration_can_be_undone(roster_database):
    ids = _seed_dated_lineups(roster_database)
    alembic(roster_database, "upgrade", AFTER_MATCH_DATE)
    alembic(roster_database, "downgrade", AFTER_DIVISION)
    with closing(sqlite3.connect(roster_database)) as db:
        columns = {r[1] for r in db.execute("PRAGMA table_info(saved_lineups)")}
        texts = {r[0]: r[1] for r in db.execute("SELECT id, date FROM saved_lineups")}
    assert not {"match_date", "match_time"} & columns
    assert texts[ids["timed"]] == "2026. 11. 24. 18:30"
    assert len(texts) == len(LEGACY_DATES)


# --- c4f8a2d6e913: match location (#294) -------------------------------------------------------

AFTER_LOCATION = "c4f8a2d6e913"


def test_location_is_added_nullable_and_can_be_undone(roster_database):
    ids = _seed_dated_lineups(roster_database)
    alembic(roster_database, "upgrade", AFTER_LOCATION)
    with closing(sqlite3.connect(roster_database)) as db:
        columns = {r[1] for r in db.execute("PRAGMA table_info(saved_lineups)")}
        locations = {r[0] for r in db.execute("SELECT location FROM saved_lineups")}
    assert "location" in columns
    assert locations == {None}
    alembic(roster_database, "downgrade", AFTER_MATCH_DATE)
    with closing(sqlite3.connect(roster_database)) as db:
        columns = {r[1] for r in db.execute("PRAGMA table_info(saved_lineups)")}
        count = db.execute("SELECT count(*) FROM saved_lineups").fetchone()[0]
    assert "location" not in columns
    assert count == len(ids)


# --- e7a2c9b4d581: team staff (#292) ---------------------------------------------------------

BEFORE_STAFF = "c4f8a2d6e913"
AFTER_STAFF = "e7a2c9b4d581"


@pytest.fixture
def staff_database(tmp_path):
    path = tmp_path / "staff.db"
    alembic(path, "upgrade", BEFORE_STAFF)
    return path


def _seed_team_and_player(path) -> dict[str, str]:
    ids = {"team": _id(), "player": _id(), "user": _id()}
    with closing(sqlite3.connect(path)) as db:
        db.execute(
            "INSERT INTO teams VALUES (?, 'T', ?, 1, '2026-11-01 10:00:00', NULL)",
            (ids["team"], ids["user"]),
        )
        db.execute(
            "INSERT INTO players VALUES (?, 'P', 'N1', ?, ?, '2026-11-01 10:00:00')",
            (ids["player"], ids["team"], ids["user"]),
        )
        db.commit()
    return ids


def _tables(path) -> set[str]:
    with closing(sqlite3.connect(path)) as db:
        return {r[0] for r in db.execute("SELECT name FROM sqlite_master")}


def test_the_staff_migration_creates_an_empty_table_and_keeps_existing_rows(
    staff_database,
):
    _seed_team_and_player(staff_database)
    alembic(staff_database, "upgrade", AFTER_STAFF)
    assert "team_staff" in _tables(staff_database)
    assert _count(staff_database, "SELECT count(*) FROM team_staff") == 0
    assert _count(staff_database, "SELECT count(*) FROM teams") == 1
    assert _count(staff_database, "SELECT count(*) FROM players") == 1
    assert {
        "ix_team_staff_team_id",
        "ix_team_staff_source_player_id",
        "ux_team_staff_default_role",
    } <= _indexes(staff_database)


def test_the_staff_table_enforces_its_rules_and_defaults(staff_database):
    ids = _seed_team_and_player(staff_database)
    alembic(staff_database, "upgrade", AFTER_STAFF)
    insert = (
        "INSERT INTO team_staff (id, team_id, role, name, created_by, is_default) "
        "VALUES (?, ?, ?, 'N', ?, ?)"
    )
    with closing(sqlite3.connect(staff_database)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        # hand-written insert: is_default and created_at fall back to their server defaults
        db.execute(
            "INSERT INTO team_staff (id, team_id, role, name, created_by) "
            "VALUES (?, ?, 'coach', 'N', ?)",
            (_id(), ids["team"], ids["user"]),
        )
        assert db.execute(
            "SELECT is_default, created_at IS NOT NULL FROM team_staff"
        ).fetchone() == (0, 1)
        db.execute(insert, (_id(), ids["team"], "coach", ids["user"], 1))
        with pytest.raises(sqlite3.IntegrityError):  # a second default for the role
            db.execute(insert, (_id(), ids["team"], "coach", ids["user"], 1))
        db.execute(insert, (_id(), ids["team"], "team_leader", ids["user"], 1))
        with pytest.raises(sqlite3.IntegrityError):  # no doctor
            db.execute(insert, (_id(), ids["team"], "doctor", ids["user"], 0))
        # the source link is nulled when the player goes, the team takes its staff along
        db.execute(
            "UPDATE team_staff SET source_player_id = ? WHERE role = 'team_leader'",
            (ids["player"],),
        )
        db.execute("DELETE FROM players WHERE id = ?", (ids["player"],))
        assert db.execute(
            "SELECT source_player_id FROM team_staff WHERE role = 'team_leader'"
        ).fetchone() == (None,)
        db.execute("DELETE FROM teams WHERE id = ?", (ids["team"],))
        assert db.execute("SELECT count(*) FROM team_staff").fetchone() == (0,)


def test_the_staff_migration_can_be_undone(staff_database):
    alembic(staff_database, "upgrade", AFTER_STAFF)
    alembic(staff_database, "downgrade", BEFORE_STAFF)
    assert "team_staff" not in _tables(staff_database)
    assert "ux_team_staff_default_role" not in _indexes(staff_database)


# --- b3e8d1f6a924: saved lineup updated_at (#290) ---------------------------------------------

AFTER_UPDATED_AT = "b3e8d1f6a924"


def _saved_lineup_columns(path) -> dict[str, tuple]:
    """`PRAGMA table_info` of saved_lineups by column name: (type, notnull, default, ...)."""
    with closing(sqlite3.connect(path)) as db:
        return {r[1]: r[2:] for r in db.execute("PRAGMA table_info(saved_lineups)")}


def test_updated_at_is_backfilled_from_created_at_and_required(staff_database):
    ids = _seed_dated_lineups(staff_database)
    alembic(staff_database, "upgrade", AFTER_STAFF)
    alembic(staff_database, "upgrade", AFTER_UPDATED_AT)
    column = _saved_lineup_columns(staff_database)["updated_at"]
    assert column[1] == 1  # NOT NULL
    assert column[2] is not None  # a server default, for hand-written inserts
    with closing(sqlite3.connect(staff_database)) as db:
        rows = db.execute("SELECT created_at, updated_at FROM saved_lineups").fetchall()
        assert len(rows) == len(ids)
        assert all(created == updated for created, updated in rows)
        # a hand-written insert that never heard of the column still works (on SQLite
        # created_at has no server default, only on Postgres: f2c8a5d7e931)
        db.execute(
            "INSERT INTO saved_lineups (id, team_id, team_name, opponent_name, "
            "match_name, division, cap, date, coach, created_by, created_at) "
            "VALUES (?, ?, 'A', 'B', 'A - B', 'D', 'Fehér', 'd', 'c', ?, "
            "'2026-11-01 10:00:00')",
            (_id(), _id(), _id()),
        )
        assert db.execute(
            "SELECT count(*) FROM saved_lineups WHERE updated_at IS NULL"
        ).fetchone() == (0,)


def test_the_updated_at_migration_can_be_undone(staff_database):
    ids = _seed_dated_lineups(staff_database)
    alembic(staff_database, "upgrade", AFTER_UPDATED_AT)
    alembic(staff_database, "downgrade", AFTER_STAFF)
    assert "updated_at" not in _saved_lineup_columns(staff_database)
    assert _count(staff_database, "SELECT count(*) FROM saved_lineups") == len(ids)
