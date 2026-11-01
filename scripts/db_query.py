"""Run one read-only SQL statement against the Supabase database (``task db:query``).

Usage (from ``backend/``)::

    task db:query -- "select count(*) from teams"
    task db:query -- --owner "select * from team_members"

By default it connects as the app role (``DATABASE_URL`` in ``backend/.env``), the same
identity the API uses, so row-level security applies. ``--owner`` uses the table owner from
``backend/.env.migrate`` (``MIGRATE_DATABASE_URL``), which sees every row; use it for admin
questions, never for changes (see ``documentation/Supabase-Admin-Guide.md``).

Two guards against slips, neither a security boundary (the role's grants are): the statement
runs inside ``BEGIN READ ONLY ... ROLLBACK`` with a 30 s statement timeout, so it works through
the transaction pooler (a session-level ``SET`` would not); and the connection URL is split into
``PG*`` environment variables for ``psql`` instead of being passed on its command line, and is
never printed, so neither the screen nor ``ps`` shows the password.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

TIMEOUT = "30s"
ASSIGNMENT = re.compile(r"^\s*(?P<key>[A-Z_]+)\s*=\s*(?P<value>.*?)\s*$")


def read_setting(path: Path, key: str) -> str | None:
    """Return the last uncommented ``key=value`` in a ``.env`` file, without quotes."""
    if not path.exists():
        return None
    found = None
    for line in path.read_text().splitlines():
        match = ASSIGNMENT.match(line)
        if match and match["key"] == key and not line.lstrip().startswith("#"):
            value = match["value"]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            found = value
    return found


def libpq_environment(url: str) -> dict[str, str]:
    """Split a SQLAlchemy/asyncpg style Postgres URL into libpq ``PG*`` variables.

    ``ssl=`` becomes ``PGSSLMODE`` and other driver-only query parameters are dropped, which
    is what stops ``psql`` from rejecting the URL. Raises ``ValueError`` for a non-Postgres
    URL (such as the SQLite default).
    """
    parts = urlsplit(url)
    if not parts.scheme.startswith(("postgres", "postgresql")) or not parts.hostname:
        raise ValueError("The URL is not a Postgres URL.")
    query = parse_qs(parts.query)
    env = {
        "PGHOST": parts.hostname,
        "PGPORT": str(parts.port or 5432),
        "PGDATABASE": unquote(parts.path.lstrip("/")) or "postgres",
        "PGSSLMODE": (query.get("sslmode") or query.get("ssl") or ["require"])[0],
    }
    if parts.username:
        env["PGUSER"] = unquote(parts.username)
    if parts.password:
        env["PGPASSWORD"] = unquote(parts.password)
    return env


def wrap(sql: str) -> str:
    """Put ``sql`` inside a read-only transaction that is always rolled back."""
    body = sql.strip().rstrip(";")
    return (
        f"BEGIN READ ONLY;\nSET LOCAL statement_timeout = '{TIMEOUT}';\n{body};\nROLLBACK;\n"
    )


def main(argv: list[str]) -> int:
    """Parse the arguments, find the URL and run ``psql`` on the wrapped statement."""
    owner = "--owner" in argv
    args = [arg for arg in argv if arg != "--owner"]
    if len(args) != 1 or not args[0].strip():
        print('Usage: task db:query -- [--owner] "SQL"', file=sys.stderr)
        return 2
    if owner:
        url = read_setting(Path(".env.migrate"), "MIGRATE_DATABASE_URL")
        source = "MIGRATE_DATABASE_URL in backend/.env.migrate"
    else:
        url = read_setting(Path(".env"), "DATABASE_URL")
        source = "DATABASE_URL in backend/.env"
    if not url:
        print(f"{source} is not set.", file=sys.stderr)
        return 1
    try:
        pg_env = libpq_environment(url)
    except ValueError:
        print(
            f"{source} is not a Postgres URL (run task db:postgres first).",
            file=sys.stderr,
        )
        return 1
    psql = shutil.which("psql")
    if not psql:
        print(
            "psql is not installed (the PostgreSQL client tools, see documentation/Setup.md).",
            file=sys.stderr,
        )
        return 1
    result = subprocess.run(  # noqa: S603 - fixed program, constant arguments
        [psql, "--no-psqlrc", "--quiet", "--set=ON_ERROR_STOP=1", "--file=-"],
        input=wrap(args[0]),
        text=True,
        env={**os.environ, **pg_env},
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
