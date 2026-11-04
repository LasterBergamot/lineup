"""Prepare the database of a self-hosted install: run the migrations, then enable the app role.

Run as `python -m lineup.db.selfhost_bootstrap` by the `migrate` service of the self-hosted
stack, from `backend/` (Alembic's config and paths are relative to it). On every start and
update it does two things, in this order:

1. `alembic upgrade head` as the table owner. The `rls_and_least_privilege_role` migration
   creates `lineup_app` as NOLOGIN.
2. Gives `lineup_app` a password and login, reusing `set_role_password` from `app_role.py`.

Reads:
  MIGRATE_DATABASE_URL  the connection as the table owner (the `api` service never sees it)
  LINEUP_APP_PASSWORD   the password to set for `lineup_app`; the `api` service uses it in its
                        own `DATABASE_URL`

Both steps are idempotent, so re-running on every start is safe. Unlike `app_role.py` this never
touches a `.env` file and generates no password: the install script owns the secrets. Nothing
secret is printed; on a failure only the exception class is shown, because driver messages can
quote statements or connection details.
"""

import asyncio
import os
import sys

from alembic.config import Config

from alembic import command
from lineup.db.app_role import set_role_password
from lineup.db.urls import to_asyncpg_url

ALEMBIC_INI = "alembic.ini"


def _read_required(name: str) -> str:
    """The environment variable `name`, or `ValueError` naming it when unset or blank."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is not set")
    return value


def main() -> int:
    """Command-line entry point; returns the process exit code (0 done, 1 failed).

    Validates both variables before touching the database, so a missing one never leaves the
    schema half-prepared. A missing variable is reported by name (it is not a secret); any other
    failure is reported by exception class only.
    """
    try:
        migrate_url = to_asyncpg_url(_read_required("MIGRATE_DATABASE_URL"))
        password = _read_required("LINEUP_APP_PASSWORD")
    except ValueError as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        return 1

    try:
        # Alembic's env.py reads MIGRATE_DATABASE_URL from the environment itself.
        command.upgrade(Config(ALEMBIC_INI), "head")
        asyncio.run(set_role_password(migrate_url, password))
    except Exception as exc:  # noqa: BLE001 - CLI boundary: report any failure, exit 1
        # Deliberately not str(exc): it can contain the statement or connection details.
        print(f"Failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    print("Migrations are up to date and the lineup_app role can log in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
