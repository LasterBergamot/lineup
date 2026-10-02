"""Tests for lineup/db/engine.py."""

from unittest.mock import Mock

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import lineup.db.engine as engine_module


async def test_get_session_yields_async_session(monkeypatch):
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(engine_module, "AsyncSessionLocal", factory)

    agen = engine_module.get_session()
    session = await agen.__anext__()
    try:
        assert isinstance(session, AsyncSession)
    finally:
        await agen.aclose()
        await test_engine.dispose()


async def test_enable_sqlite_foreign_keys_registers_listener_for_sqlite(monkeypatch):
    spy = Mock(wraps=event.listens_for)
    monkeypatch.setattr(engine_module.event, "listens_for", spy)
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        engine_module.enable_sqlite_foreign_keys(test_engine)
        spy.assert_called_once_with(test_engine.sync_engine, "connect")
    finally:
        await test_engine.dispose()


async def test_enable_sqlite_foreign_keys_is_noop_for_postgres(monkeypatch):
    spy = Mock(wraps=event.listens_for)
    monkeypatch.setattr(engine_module.event, "listens_for", spy)
    # Engines are lazy: nothing connects until first use, so this needs no server.
    test_engine = create_async_engine("postgresql+asyncpg://user:pw@localhost:5432/db")
    try:
        engine_module.enable_sqlite_foreign_keys(test_engine)
        spy.assert_not_called()
    finally:
        await test_engine.dispose()


async def test_enable_sqlite_foreign_keys_sets_pragma_on_connect():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    engine_module.enable_sqlite_foreign_keys(test_engine)
    try:
        async with test_engine.connect() as conn:
            result = await conn.exec_driver_sql("PRAGMA foreign_keys")
            assert result.scalar() == 1
    finally:
        await test_engine.dispose()


def test_make_engine_kwargs_for_postgres_is_pooler_safe():
    kwargs = engine_module._make_engine_kwargs(
        "postgresql+asyncpg://user:pw@host:6543/db"
    )
    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"] == {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": engine_module._unique_statement_name,
    }


def test_unique_statement_name_differs_per_call():
    first = engine_module._unique_statement_name()
    second = engine_module._unique_statement_name()

    assert first != second
    assert first.startswith("__asyncpg_")
    assert first.endswith("__")


def test_make_engine_kwargs_empty_for_sqlite():
    assert engine_module._make_engine_kwargs("sqlite+aiosqlite:///./lineup.db") == {}
