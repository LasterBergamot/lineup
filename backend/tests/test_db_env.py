"""scripts/db_env.py (task db:status / db:sqlite / db:postgres): DATABASE_URL and ENV must move
together, whatever shape the saved URL has (#75)."""

import importlib.util
import stat
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "db_env.py"
spec = importlib.util.spec_from_file_location("db_env", SCRIPT)
db_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(db_env)

POOLER = "postgresql+asyncpg://lineup_app.ref:secret@aws-0-eu.pooler.supabase.com:6543/postgres?ssl=require"
SESSION = "postgresql+asyncpg://postgres.ref:secret@aws-0-eu.pooler.supabase.com:5432/postgres?ssl=require"


def run(tmp_path, capsys, command, text=None):
    env = tmp_path / ".env"
    if text is not None:
        env.write_text(text)
        env.chmod(0o600)
    code = db_env.main([command, str(env)])
    return code, capsys.readouterr(), env


def test_unknown_command_prints_usage(capsys):
    assert db_env.main([]) == 2
    assert "status|sqlite|postgres" in capsys.readouterr().err


def test_status_without_a_file_is_sqlite(tmp_path, capsys):
    code, out, _ = run(tmp_path, capsys, "status")
    assert code == 0
    assert "sqlite" in out.out and "ENV=(unset)" in out.out and "WARNING" not in out.out


def test_status_postgres_with_env_production_is_clean(tmp_path, capsys):
    _, out, _ = run(
        tmp_path, capsys, "status", f'DATABASE_URL="{POOLER}"\nENV=production\n'
    )
    assert "postgres (Supabase pooler: aws-0-eu.pooler.supabase.com)" in out.out
    assert "WARNING" not in out.out
    assert "secret" not in out.out


def test_status_warns_when_postgres_runs_without_env_production(tmp_path, capsys):
    _, out, _ = run(tmp_path, capsys, "status", f'DATABASE_URL="{POOLER}"\n')
    assert "WARNING" in out.out and "fail-closed" in out.out


def test_status_warns_when_sqlite_runs_with_env_production(tmp_path, capsys):
    _, out, _ = run(
        tmp_path, capsys, "status", f'# DATABASE_URL="{POOLER}"\nENV=production\n'
    )
    assert (
        "sqlite" in out.out and "WARNING" in out.out and "refuses to start" in out.out
    )


def test_the_last_active_url_wins(tmp_path, capsys):
    text = f'DATABASE_URL="{POOLER}"\nDATABASE_URL="sqlite+aiosqlite:///./x.db"\n'
    _, out, _ = run(tmp_path, capsys, "status", text)
    assert out.out.startswith("sqlite")


def test_sqlite_comments_out_a_session_pooler_url_too(tmp_path, capsys):
    """The old sed only matched port 6543, leaving a 5432 URL live without ENV=production."""
    code, _, env = run(
        tmp_path,
        capsys,
        "sqlite",
        f'DATABASE_URL="{SESSION}"\nENV=production\nOTHER=1\n',
    )
    assert code == 0
    assert env.read_text() == f'# DATABASE_URL="{SESSION}"\nOTHER=1\n'


def test_sqlite_handles_unquoted_urls_and_keeps_the_file_mode(tmp_path, capsys):
    _, _, env = run(
        tmp_path, capsys, "sqlite", f"DATABASE_URL={POOLER}\nENV=production\n"
    )
    assert env.read_text().startswith("# DATABASE_URL=")
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_sqlite_without_a_file_does_nothing(tmp_path, capsys):
    code, out, env = run(tmp_path, capsys, "sqlite")
    assert code == 0 and not env.exists() and "already on SQLite" in out.out


@pytest.mark.parametrize("prefix", ["# ", "#"])
def test_postgres_uncomments_the_saved_url_with_or_without_a_space(
    tmp_path, capsys, prefix
):
    """The old grep accepted `#DATABASE_URL=` but the sed only `# DATABASE_URL`."""
    code, _, env = run(
        tmp_path, capsys, "postgres", f'{prefix}DATABASE_URL="{POOLER}"\n'
    )
    assert code == 0
    assert env.read_text() == f'DATABASE_URL="{POOLER}"\nENV=production\n'
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_postgres_skips_placeholders_and_non_pooler_urls(tmp_path, capsys):
    text = (
        '# DATABASE_URL="postgresql+asyncpg://postgres.<ref>:<pw>@host:6543/postgres"\n'
        f'# DATABASE_URL="{SESSION}"\n'
    )
    code, out, env = run(tmp_path, capsys, "postgres", text)
    assert code == 1 and "No filled-in pooler" in out.err
    assert env.read_text() == text


def test_postgres_without_a_file_fails(tmp_path, capsys):
    code, out, _ = run(tmp_path, capsys, "postgres")
    assert code == 1 and "No filled-in pooler" in out.err


def test_postgres_replaces_a_different_env_and_keeps_an_active_url(tmp_path, capsys):
    _, _, env = run(
        tmp_path,
        capsys,
        "postgres",
        f'DATABASE_URL="{POOLER}"\nENV=development\nENV=\n',
    )
    assert env.read_text() == f'DATABASE_URL="{POOLER}"\nENV=production\n'


def test_a_failed_write_leaves_the_original_and_no_temp_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("A=1\n")

    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(db_env.os, "replace", boom)
    with pytest.raises(OSError):
        db_env.write(env, ["B=2"])
    assert env.read_text() == "A=1\n"
    assert [p.name for p in tmp_path.iterdir()] == [".env"]
