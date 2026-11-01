"""scripts/db_query.py (task db:query): read-only psql that never shows the connection URL (#75)."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "db_query.py"
spec = importlib.util.spec_from_file_location("db_query", SCRIPT)
db_query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_query)

URL = "postgresql+asyncpg://lineup_app.ref:p%40ss@aws-0-eu.pooler.supabase.com:6543/postgres?ssl=require&prepared_statement_cache_size=0"


def test_libpq_environment_splits_the_url_and_drops_driver_parameters():
    env = db_query.libpq_environment(URL)
    assert env == {
        "PGHOST": "aws-0-eu.pooler.supabase.com",
        "PGPORT": "6543",
        "PGDATABASE": "postgres",
        "PGSSLMODE": "require",
        "PGUSER": "lineup_app.ref",
        "PGPASSWORD": "p@ss",
    }


def test_libpq_environment_defaults_and_sslmode():
    env = db_query.libpq_environment(
        "postgresql://db.example.com/app?sslmode=verify-full"
    )
    assert env == {
        "PGHOST": "db.example.com",
        "PGPORT": "5432",
        "PGDATABASE": "app",
        "PGSSLMODE": "verify-full",
    }


@pytest.mark.parametrize("url", ["sqlite+aiosqlite:///./lineup.db", "postgresql://"])
def test_libpq_environment_rejects_other_urls(url):
    with pytest.raises(ValueError):
        db_query.libpq_environment(url)


def test_wrap_is_read_only_and_always_rolls_back():
    sql = db_query.wrap("  select 1;  ")
    assert sql.startswith("BEGIN READ ONLY;")
    assert "statement_timeout" in sql
    assert "select 1;\nROLLBACK;" in sql


def test_read_setting_ignores_comments_and_strips_quotes(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        '# DATABASE_URL="old"\nDATABASE_URL="first"\nDATABASE_URL=\'second\'\n'
    )
    assert db_query.read_setting(env, "DATABASE_URL") == "second"
    assert db_query.read_setting(env, "MISSING") is None
    assert db_query.read_setting(tmp_path / "nope", "DATABASE_URL") is None


@pytest.fixture
def in_backend(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_usage_error(in_backend, capsys):
    assert db_query.main([]) == 2
    assert db_query.main(["a", "b"]) == 2
    assert "Usage" in capsys.readouterr().err


def test_missing_url_and_wrong_url(in_backend, capsys):
    assert db_query.main(["select 1"]) == 1
    assert "DATABASE_URL in backend/.env is not set" in capsys.readouterr().err
    (in_backend / ".env").write_text('DATABASE_URL="sqlite+aiosqlite:///./lineup.db"\n')
    assert db_query.main(["select 1"]) == 1
    assert "not a Postgres URL" in capsys.readouterr().err


def test_missing_psql(in_backend, capsys, monkeypatch):
    (in_backend / ".env").write_text(f'DATABASE_URL="{URL}"\n')
    monkeypatch.setattr(db_query.shutil, "which", lambda _: None)
    assert db_query.main(["select 1"]) == 1
    assert "psql is not installed" in capsys.readouterr().err


def test_runs_psql_with_the_url_only_in_the_environment(
    in_backend, capsys, monkeypatch
):
    (in_backend / ".env").write_text(f'DATABASE_URL="{URL}"\n')
    monkeypatch.setattr(db_query.shutil, "which", lambda _: "/usr/bin/psql")
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(args=args, **kwargs)
        return subprocess.CompletedProcess(args, 3)

    monkeypatch.setattr(db_query.subprocess, "run", fake_run)
    assert db_query.main(["select count(*) from teams"]) == 3
    assert seen["env"]["PGPASSWORD"] == "p@ss"
    assert seen["input"].startswith("BEGIN READ ONLY;")
    joined = " ".join(seen["args"])
    assert "p@ss" not in joined and "pooler" not in joined
    captured = capsys.readouterr()
    assert "p@ss" not in captured.out + captured.err


def test_owner_reads_the_migrate_file(in_backend, monkeypatch):
    (in_backend / ".env").write_text('DATABASE_URL="postgresql://app:x@h/db"\n')
    (in_backend / ".env.migrate").write_text(
        'MIGRATE_DATABASE_URL="postgresql://owner:y@h/db"\n'
    )
    monkeypatch.setattr(db_query.shutil, "which", lambda _: "/usr/bin/psql")
    seen = {}
    monkeypatch.setattr(
        db_query.subprocess,
        "run",
        lambda args, **kw: seen.update(kw) or subprocess.CompletedProcess(args, 0),
    )
    assert db_query.main(["--owner", "select 1"]) == 0
    assert seen["env"]["PGUSER"] == "owner"
