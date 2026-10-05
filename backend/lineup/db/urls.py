"""Helpers for database URLs that come from outside the app (dashboards, `.env` files)."""

from sqlalchemy.engine import make_url

_POSTGRES_NAMES = {"postgres", "postgresql"}


def to_asyncpg_url(url: str) -> str:
    """Return `url` rewritten to the `postgresql+asyncpg` driver this project ships.

    Supabase's dashboard hands out plain `postgresql://...` strings, which SQLAlchemy would
    pair with a sync driver (`psycopg`/`psycopg2`) that isn't installed, failing with
    `ModuleNotFoundError`. libpq's `sslmode=` query parameter is mapped to asyncpg's `ssl=`
    (same values, e.g. `require`). Non-Postgres URLs, such as SQLite, are returned unchanged.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() not in _POSTGRES_NAMES:
        return url
    query = dict(parsed.query)
    if "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    return parsed.set(drivername="postgresql+asyncpg", query=query).render_as_string(
        hide_password=False
    )
