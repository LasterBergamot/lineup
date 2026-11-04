import runpy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lineup.db import selfhost_bootstrap

URL = "postgresql://postgres:ownerpw@db:5432/lineup"
CANARY = "s3cret-app-password"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("MIGRATE_DATABASE_URL", URL)
    monkeypatch.setenv("LINEUP_APP_PASSWORD", CANARY)


@pytest.fixture
def calls():
    """Patch both steps and record the order they run in."""
    order: list[str] = []
    upgrade = MagicMock(side_effect=lambda *a, **k: order.append("upgrade"))
    set_password = AsyncMock(side_effect=lambda *a, **k: order.append("password"))
    with (
        patch.object(selfhost_bootstrap.command, "upgrade", upgrade),
        patch.object(selfhost_bootstrap, "set_role_password", set_password),
    ):
        yield order, upgrade, set_password


def test_runs_the_migrations_before_setting_the_password(env, calls, capsys):
    order, upgrade, set_password = calls
    assert selfhost_bootstrap.main() == 0
    assert order == ["upgrade", "password"]
    assert upgrade.call_args.args[1] == "head"
    # The URL is rewritten to the asyncpg driver; the password is passed through.
    set_password.assert_awaited_once_with(
        "postgresql+asyncpg://postgres:ownerpw@db:5432/lineup", CANARY
    )
    assert CANARY not in capsys.readouterr().out


@pytest.mark.parametrize("name", ["MIGRATE_DATABASE_URL", "LINEUP_APP_PASSWORD"])
@pytest.mark.parametrize("blank", [None, "", "   "])
def test_a_missing_variable_is_named_and_nothing_runs(
    env, calls, monkeypatch, capsys, name, blank
):
    order, _, _ = calls
    if blank is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, blank)
    assert selfhost_bootstrap.main() == 1
    assert f"{name} is not set" in capsys.readouterr().err
    assert order == []


def test_a_migration_failure_prints_only_the_class_name(env, calls, capsys):
    _, upgrade, set_password = calls
    upgrade.side_effect = RuntimeError(f"boom {URL} {CANARY}")
    assert selfhost_bootstrap.main() == 1
    captured = capsys.readouterr()
    assert "Failed: RuntimeError" in captured.err
    assert CANARY not in captured.err + captured.out
    assert "ownerpw" not in captured.err + captured.out
    set_password.assert_not_awaited()


def test_a_password_failure_prints_only_the_class_name(env, calls, capsys):
    _, _, set_password = calls
    set_password.side_effect = ValueError(f"role is odd {CANARY}")
    assert selfhost_bootstrap.main() == 1
    captured = capsys.readouterr()
    assert "Failed: ValueError" in captured.err
    assert CANARY not in captured.err + captured.out


def test_runs_as_a_module(monkeypatch, capsys):
    monkeypatch.delenv("MIGRATE_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("lineup.db.selfhost_bootstrap", run_name="__main__")
    assert exit_info.value.code == 1
    assert "MIGRATE_DATABASE_URL is not set" in capsys.readouterr().err
