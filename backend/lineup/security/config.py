"""Startup configuration checks: API docs exposure and the fail-closed production config.

Like `parse_cors_origins` and `read_max_concurrent`, these are small functions that take the raw
environment value and raise `ValueError` with a message naming the variable, so a bad deploy
stops at startup instead of running half-secured. Error messages never contain the values
(`DATABASE_URL` holds the database password).
"""

import logging
import os
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

logger = logging.getLogger(__name__)

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})
_ACCEPTED_SSL_MODES = frozenset({"require", "verify-full"})


def read_docs_enabled(raw: str | None, env: str | None) -> bool:
    """Whether to serve `/docs`, `/redoc` and `/openapi.json` (`DOCS_ENABLED`, default on).

    Always off when `env` is `production`, whatever `DOCS_ENABLED` says: the interactive docs
    hand an attacker a map of the API, and an operator should not be able to leave them on by
    accident. The frontend's client is generated offline by `scripts/dump_openapi.py`, which does
    not need the route. Raises `ValueError` for a value that is not a boolean word.
    """
    if env == "production":
        return False
    value = (raw or "").strip().lower()
    if not value:
        return True
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError("DOCS_ENABLED must be true or false")


def validate_production_config(environ: Mapping[str, str] | None = None) -> None:
    """Refuse to start a production deployment that would run insecurely (fail closed).

    Does nothing unless `ENV=production`. Then it collects every problem and raises one
    `ValueError` listing them all: `DATABASE_URL` must be set (otherwise the app silently falls
    back to a SQLite file inside the container), must use the `postgresql+asyncpg` driver, and
    must demand TLS with `ssl=require` or `ssl=verify-full` (`sslmode=` is accepted too). A
    `require` only encrypts, it does not check the server certificate, so it logs a warning
    recommending `verify-full`. `SUPABASE_URL` must be set, or every protected route would answer
    503. Called from the app's lifespan rather than at import, so tests and
    `scripts/dump_openapi.py` can import the app without a production environment.
    """
    env = os.environ if environ is None else environ
    if env.get("ENV") != "production":
        return

    problems: list[str] = []
    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        problems.append("DATABASE_URL is not set")
    else:
        try:
            url = make_url(database_url)
        except ArgumentError:
            problems.append("DATABASE_URL is not a valid database URL")
        else:
            if url.drivername != "postgresql+asyncpg":
                problems.append("DATABASE_URL must use the postgresql+asyncpg driver")
            ssl_mode = url.query.get("ssl") or url.query.get("sslmode")
            if ssl_mode not in _ACCEPTED_SSL_MODES:
                problems.append("DATABASE_URL must set ssl=require or ssl=verify-full")
            elif ssl_mode == "require":
                logger.warning(
                    "DATABASE_URL uses ssl=require, which encrypts but does not verify "
                    "the server certificate; prefer ssl=verify-full"
                )
    if not env.get("SUPABASE_URL", "").strip():
        problems.append("SUPABASE_URL is not set")

    if problems:
        raise ValueError(
            "Refusing to start with ENV=production: " + "; ".join(problems)
        )
