import contextlib
from unittest.mock import patch

import pytest
from sqlalchemy.engine import make_url

from lineup.db import app_role

POOLER = (
    'DATABASE_URL="postgresql+asyncpg://postgres.abcdefgh:oldpassword@'
    'aws-0-eu-central-1.pooler.supabase.com:6543/postgres?ssl=require"'
)
MIGRATE = (
    'MIGRATE_DATABASE_URL="postgresql+asyncpg://postgres:ownerpw@'
    'db.abcdefgh.supabase.co:5432/postgres?ssl=require"'
)
ENV = f"# notes\n{POOLER}\nENV=production\n"
MIGRATE_FILE = f"# owner credentials\n{MIGRATE}\n"


class TestFindMigrateUrl:
    def test_quoted(self):
        assert app_role.find_migrate_url(MIGRATE_FILE).startswith(
            "postgresql+asyncpg://postgres:ownerpw@db.abcdefgh"
        )

    def test_unquoted(self):
        url = app_role.find_migrate_url(
            "MIGRATE_DATABASE_URL=postgresql+asyncpg://u@h/d\n"
        )
        assert url == "postgresql+asyncpg://u@h/d"

    def test_commented_out_or_missing_is_an_error(self):
        with pytest.raises(ValueError, match="MIGRATE_DATABASE_URL"):
            app_role.find_migrate_url('# MIGRATE_DATABASE_URL="x"\nENV=production\n')


class TestAppRoleUrl:
    def test_swaps_user_and_password_and_keeps_host_port_and_query(self):
        new_value = "newpw"
        url = make_url(
            app_role.app_role_url(
                "postgresql+asyncpg://postgres.abcdefgh:old@host.example:6543/postgres?ssl=require",
                new_value,
            )
        )
        assert url.username == "lineup_app.abcdefgh"
        assert url.password == new_value
        assert (url.host, url.port, url.database) == ("host.example", 6543, "postgres")
        assert url.query == {"ssl": "require"}

    def test_user_without_project_ref_is_refused(self):
        with pytest.raises(ValueError, match="project-ref"):
            app_role.app_role_url("postgresql+asyncpg://postgres:pw@h:6543/d", "x")


class TestRewriteEnv:
    def test_rewrites_the_pooler_line_only(self):
        result = app_role.rewrite_env(ENV, "newpw")
        assert "lineup_app.abcdefgh:newpw@aws-0-eu-central-1" in result
        assert "oldpassword" not in result
        assert "ownerpw" not in result, "owner credentials never belong in .env"
        assert "ENV=production" in result and result.endswith("\n")

    def test_commented_pooler_line_stays_commented(self):
        result = app_role.rewrite_env(ENV.replace(POOLER, f"# {POOLER}"), "newpw")
        assert (
            '# DATABASE_URL="postgresql+asyncpg://lineup_app.abcdefgh:newpw@' in result
        )

    def test_no_trailing_newline_is_preserved(self):
        assert not app_role.rewrite_env(POOLER, "pw").endswith("\n")

    def test_missing_pooler_line_is_an_error(self):
        with pytest.raises(ValueError, match="pooler DATABASE_URL"):
            app_role.rewrite_env(MIGRATE + "\n", "pw")

    def test_direct_connection_line_is_not_a_pooler_line(self):
        direct = 'DATABASE_URL="postgresql+asyncpg://postgres:pw@db.x.supabase.co:5432/postgres"'
        with pytest.raises(ValueError, match="pooler DATABASE_URL"):
            app_role.rewrite_env(direct + "\n", "pw")


class _FakeConn:
    def __init__(self, role_exists=True):
        self.role_exists = role_exists
        self.calls = []

    async def scalar(self, statement, params=None):
        self.calls.append((str(statement), params))
        return 1 if self.role_exists else None

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params))


class _FakeEngine:
    def __init__(self, conn):
        self.conn = conn
        self.disposed = False

    @contextlib.asynccontextmanager
    async def begin(self):
        yield self.conn

    async def dispose(self):
        self.disposed = True


class TestSetRolePassword:
    async def test_sets_the_password_as_a_bound_parameter_only(self):
        conn = _FakeConn()
        engine = _FakeEngine(conn)
        with patch.object(app_role, "create_async_engine", return_value=engine):
            await app_role.set_role_password("postgresql+asyncpg://x", "s3cret")

        assert engine.disposed
        statements = [statement for statement, _ in conn.calls]
        assert not any("s3cret" in statement for statement in statements)
        assert ({"password": "s3cret"}) in [params for _, params in conn.calls]
        assert "ALTER ROLE lineup_app WITH LOGIN PASSWORD" in statements[-1]

    async def test_missing_role_points_at_the_migration(self):
        engine = _FakeEngine(_FakeConn(role_exists=False))
        with patch.object(app_role, "create_async_engine", return_value=engine):
            with pytest.raises(ValueError, match="task migrate:supabase"):
                await app_role.set_role_password("postgresql+asyncpg://x", "pw")
        assert engine.disposed


def _files(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(ENV)
    env_file.chmod(0o600)
    migrate_file = tmp_path / ".env.migrate"
    migrate_file.write_text(MIGRATE_FILE)
    return (
        env_file,
        migrate_file,
        [
            "--env-file",
            str(env_file),
            "--migrate-file",
            str(migrate_file),
        ],
    )


class TestMain:
    def test_success_rewrites_the_file_and_never_prints_the_password(
        self, tmp_path, capsys
    ):
        env_file, migrate_file, args = _files(tmp_path)
        captured = {}

        async def fake_set(url, password):
            captured["url"], captured["password"] = url, password

        with patch.object(app_role, "set_role_password", fake_set):
            assert app_role.main(args) == 0

        new_text = env_file.read_text()
        assert captured["url"].startswith("postgresql+asyncpg://postgres:ownerpw@")
        assert len(captured["password"]) == 48
        assert f"lineup_app.abcdefgh:{captured['password']}@" in new_text
        assert "ownerpw" not in new_text
        assert oct(env_file.stat().st_mode & 0o777) == "0o600"
        assert migrate_file.read_text() == MIGRATE_FILE
        out = capsys.readouterr()
        assert captured["password"] not in out.out + out.err
        assert "lineup_app" in out.out
        assert sorted(p.name for p in tmp_path.iterdir()) == [".env", ".env.migrate"], (
            "no temp files left behind"
        )

    def test_a_plain_postgresql_url_is_switched_to_the_asyncpg_driver(self, tmp_path):
        _, migrate_file, args = _files(tmp_path)
        migrate_file.write_text(
            'MIGRATE_DATABASE_URL="postgresql://postgres:ownerpw@db.abcdefgh.supabase.co:5432/postgres"\n'
        )
        captured = {}

        async def fake_set(url, password):
            captured["url"] = url

        with patch.object(app_role, "set_role_password", fake_set):
            assert app_role.main(args) == 0
        assert captured["url"].startswith("postgresql+asyncpg://postgres:ownerpw@")

    def test_database_failure_leaves_the_file_untouched_and_hides_details(
        self, tmp_path, capsys
    ):
        env_file, _, args = _files(tmp_path)

        async def failing_set(url, password):
            raise ConnectionError(f"could not connect to {url} with {password}")

        with patch.object(app_role, "set_role_password", failing_set):
            assert app_role.main(args) == 1

        assert env_file.read_text() == ENV
        err = capsys.readouterr().err
        assert "ConnectionError" in err
        assert "ownerpw" not in err and "could not connect" not in err

    def test_missing_migrate_url_is_reported_in_words(self, tmp_path, capsys):
        _, migrate_file, args = _files(tmp_path)
        migrate_file.write_text("# nothing here\n")
        assert app_role.main(args) == 1
        assert "MIGRATE_DATABASE_URL" in capsys.readouterr().err

    def test_missing_pooler_url_is_reported_in_words(self, tmp_path, capsys):
        env_file, _, args = _files(tmp_path)
        env_file.write_text("ENV=production\n")
        assert app_role.main(args) == 1
        assert "pooler DATABASE_URL" in capsys.readouterr().err

    def test_missing_file_is_a_clean_failure(self, tmp_path, capsys):
        assert app_role.main(["--env-file", str(tmp_path / "nope")]) == 1
        assert "FileNotFoundError" in capsys.readouterr().err


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_running_the_module_exits_with_main_s_status(tmp_path, monkeypatch):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["app_role", "--env-file", str(tmp_path / "nope")])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("lineup.db.app_role", run_name="__main__")
    assert exit_info.value.code == 1
