"""Tests for lineup/db/connection_settings.py."""

import pytest
from sqlalchemy.pool import NullPool

import lineup.db.connection_settings as settings


def test_make_engine_kwargs_for_postgres_is_pooler_safe():
    kwargs = settings.make_engine_kwargs("postgresql+asyncpg://user:pw@host:6543/db")
    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"] == {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": settings._unique_statement_name,
    }


def test_unique_statement_name_differs_per_call():
    first = settings._unique_statement_name()
    second = settings._unique_statement_name()

    assert first != second
    assert first.startswith("__asyncpg_")
    assert first.endswith("__")


def test_make_engine_kwargs_empty_for_sqlite():
    assert settings.make_engine_kwargs("sqlite+aiosqlite:///./lineup.db") == {}


POSTGRES = "postgresql+asyncpg://user:pw@host:6543/db?ssl=require"
SQLITE = "sqlite+aiosqlite:///./lineup.db"


@pytest.mark.parametrize("flag", ["1", "true", "TRUE", " yes "])
def test_auto_create_runs_on_sqlite_when_opted_in(flag):
    assert settings.auto_create_schema_enabled(SQLITE, flag) is True


@pytest.mark.parametrize("flag", [None, "", "0", "false", "no"])
def test_auto_create_needs_an_explicit_opt_in(flag):
    assert settings.auto_create_schema_enabled(SQLITE, flag) is False


@pytest.mark.parametrize("flag", [None, "1", "true"])
def test_auto_create_never_runs_on_postgres(flag):
    assert settings.auto_create_schema_enabled(POSTGRES, flag) is False
