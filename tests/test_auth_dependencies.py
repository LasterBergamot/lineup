"""Tests for lineup/auth/dependencies.py."""

from lineup.auth.dependencies import get_current_user_id


async def test_get_current_user_id_returns_none():
    assert await get_current_user_id() is None
