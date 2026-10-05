"""Give the `lineup_app` database role a password and point backend/.env at it.

Run with `task db:create-app-role`. The role itself is created (NOLOGIN, no BYPASSRLS, DML
on the app tables only) by the `rls_and_least_privilege_role` migration; this script does the
part that must not live in git: generate a password, enable login, and write the matching
pooler URL into `backend/.env`.

Reads:
  backend/.env.migrate  MIGRATE_DATABASE_URL, the Supabase direct/session connection as the
                        table owner (sets the role). Kept out of `.env` on purpose: Compose
                        and `task serve` load `.env` into the API's environment, and the API
                        must never see the owner's credentials.
  backend/.env          DATABASE_URL, the pooler URL (port 6543) whose user and password
                        get replaced

The password is never printed. On any failure only the exception class is shown, because
SQLAlchemy/asyncpg messages can quote the statement.
"""

import argparse
import asyncio
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

APP_ROLE = "lineup_app"

_POOLER_LINE = re.compile(
    r'^(?P<prefix>#\s*)?DATABASE_URL="(?P<url>postgresql\+asyncpg://[^"<>]*:6543/[^"]*)"\s*$'
)
_MIGRATE_LINE = re.compile(r'^MIGRATE_DATABASE_URL="?(?P<url>[^"\s]+)"?\s*$')

# The password travels as a bound parameter into a session setting and is only formatted
# server-side (%L quotes it), so it never appears in the SQL text we send.
_ALTER_ROLE = f"""
DO $$
BEGIN
  EXECUTE format(
    'ALTER ROLE {APP_ROLE} WITH LOGIN PASSWORD %L',
    current_setting('lineup.app_password')
  );
END $$;
"""


def find_migrate_url(env_text: str) -> str:
    for line in env_text.splitlines():
        match = _MIGRATE_LINE.match(line)
        if match:
            return match.group("url")
    raise ValueError("MIGRATE_DATABASE_URL is not set in the migrate file")


def app_role_url(pooler_url: str, password: str) -> str:
    """The pooler URL with the user swapped to `lineup_app.<project-ref>`."""
    url = make_url(pooler_url)
    _, _, project_ref = (url.username or "").partition(".")
    if not project_ref:
        raise ValueError(
            "expected a Supabase pooler user like 'postgres.<project-ref>' in DATABASE_URL"
        )
    return url.set(
        username=f"{APP_ROLE}.{project_ref}", password=password
    ).render_as_string(hide_password=False)


def rewrite_env(env_text: str, password: str) -> str:
    """Replace user and password in every pooler DATABASE_URL line, commented or not."""
    found = False
    lines = []
    for line in env_text.splitlines():
        match = _POOLER_LINE.match(line)
        if match:
            found = True
            new_url = app_role_url(match.group("url"), password)
            line = f'{match.group("prefix") or ""}DATABASE_URL="{new_url}"'
        lines.append(line)
    if not found:
        raise ValueError(
            "no pooler DATABASE_URL (port 6543) found; fill it in first (see .env.example)"
        )
    return "\n".join(lines) + ("\n" if env_text.endswith("\n") else "")


async def set_role_password(migrate_url: str, password: str) -> None:
    engine = create_async_engine(migrate_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
                {"role": APP_ROLE},
            )
            if not exists:
                raise ValueError(
                    f"role {APP_ROLE} does not exist; run `task migrate:supabase` first"
                )
            await conn.execute(
                text("SELECT set_config('lineup.app_password', :password, true)"),
                {"password": password},
            )
            await conn.execute(text(_ALTER_ROLE))
    finally:
        await engine.dispose()


def _write_atomically(path: Path, content: str) -> None:
    mode = path.stat().st_mode & 0o777
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, delete=False, prefix=".env."
    ) as tmp:
        tmp.write(content)
    os.chmod(tmp.name, mode)
    os.replace(tmp.name, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--migrate-file", type=Path, default=Path(".env.migrate"))
    args = parser.parse_args(argv)

    try:
        env_text = args.env_file.read_text()
        migrate_url = find_migrate_url(args.migrate_file.read_text())
        password = secrets.token_hex(24)
        new_env = rewrite_env(env_text, password)
        asyncio.run(set_role_password(migrate_url, password))
        _write_atomically(args.env_file, new_env)
    except Exception as exc:
        # Deliberately not str(exc): it can contain the statement or connection details.
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(f"Failed: {reason}", file=sys.stderr)
        return 1

    print(f"Role {APP_ROLE} can now log in; its password was not printed.")
    print(f"{args.env_file} now points DATABASE_URL at {APP_ROLE} (pooler, port 6543).")
    print(
        "Restart task serve / run task up to use it, then run the supabase-smoke skill."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
