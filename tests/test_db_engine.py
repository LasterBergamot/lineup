"""Tests for lineup/db/engine.py."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
