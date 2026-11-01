"""Switch ``backend/.env`` between local SQLite and the Supabase pooler (``task db:*``).

The app picks its database from ``DATABASE_URL`` and, separately, decides from ``ENV`` whether
to fail closed at startup. The two have to move together: a Postgres URL with ``ENV`` unset
skips the checks that insist on TLS and switch the API docs off, and ``ENV=production`` with
SQLite makes the app refuse to start. So every command here changes both, and ``status`` warns when
they disagree.

Usage (from ``backend/``, which is where ``task`` runs it)::

    python3 ../scripts/db_env.py status|sqlite|postgres [path/to/.env]

The URL is never printed (it holds the password); only its host is.
"""

import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

URL_LINE = re.compile(r"^(?P<hash>#\s*)?DATABASE_URL\s*=\s*(?P<value>.*?)\s*$")
ENV_LINE = re.compile(r"^(?P<hash>#\s*)?ENV\s*=\s*(?P<value>.*?)\s*$")
POOLER_PORT = ":6543/"


def unquote(value: str) -> str:
    """Return a ``.env`` value without its surrounding quotes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def is_postgres(value: str) -> bool:
    """Whether a (possibly quoted) ``DATABASE_URL`` value points at Postgres."""
    return unquote(value).startswith(("postgres://", "postgresql://", "postgresql+"))


def is_filled_in(value: str) -> bool:
    """Whether a URL is real, not the ``<placeholder>`` line from ``.env.example``."""
    return "<" not in value and ">" not in value


def active_url(lines: list[str]) -> str | None:
    """The ``DATABASE_URL`` the app would use: the last uncommented one, or ``None``."""
    found = None
    for line in lines:
        match = URL_LINE.match(line)
        if match and not match["hash"]:
            found = unquote(match["value"])
    return found


def env_value(lines: list[str]) -> str | None:
    """The effective ``ENV`` (last uncommented assignment), or ``None`` when unset."""
    found = None
    for line in lines:
        match = ENV_LINE.match(line)
        if match and not match["hash"]:
            found = unquote(match["value"])
    return found


def status(lines: list[str]) -> tuple[str, list[str]]:
    """Describe the active database and list the ``ENV`` mismatches worth a warning."""
    url = active_url(lines)
    env = env_value(lines)
    warnings = []
    if url and is_postgres(url):
        host = urlsplit(url.replace("+asyncpg", "", 1)).hostname or "unknown host"
        text = f"postgres (Supabase pooler: {host})"
        if env != "production":
            warnings.append(
                "ENV is not 'production': the app skips its fail-closed startup checks (TLS "
                "required, docs off) for this Postgres database. Run `task db:postgres` to "
                "fix it."
            )
    else:
        text = "sqlite (local backend/lineup.db)"
        if env == "production":
            warnings.append(
                "ENV=production with SQLite: the app refuses to start (it needs a Postgres "
                "URL). Run `task db:sqlite` to fix it."
            )
    text += f", ENV={env if env is not None else '(unset)'}"
    return text, warnings


def to_sqlite(lines: list[str]) -> list[str]:
    """Comment out every active Postgres ``DATABASE_URL`` (any port) and drop ``ENV=production``."""
    out = []
    for line in lines:
        url = URL_LINE.match(line)
        if url and not url["hash"] and is_postgres(url["value"]):
            out.append(f"# {line}")
            continue
        env = ENV_LINE.match(line)
        if env and not env["hash"] and unquote(env["value"]) == "production":
            continue
        out.append(line)
    return out


def to_postgres(lines: list[str]) -> list[str]:
    """Uncomment the saved, filled-in pooler URL and make sure ``ENV=production`` is set.

    Raises ``ValueError`` when there is neither an active nor a saved pooler URL.
    """
    out = list(lines)
    active = active_url(out)
    if not (active and is_postgres(active)):
        for index, line in enumerate(out):
            match = URL_LINE.match(line)
            if (
                match
                and match["hash"]
                and is_postgres(match["value"])
                and is_filled_in(match["value"])
                and POOLER_PORT in match["value"]
            ):
                out[index] = f"DATABASE_URL={match['value']}"
                break
        else:
            raise ValueError(
                "No filled-in pooler DATABASE_URL (port 6543) found in backend/.env. Copy "
                "backend/.env.example to backend/.env and add your Supabase URL first."
            )
    replaced = False
    result = []
    for line in out:
        match = ENV_LINE.match(line)
        if match and not match["hash"]:
            if not replaced:
                result.append("ENV=production")
                replaced = True
            continue
        result.append(line)
    if not replaced:
        result.append("ENV=production")
    return result


def write(path: Path, lines: list[str]) -> None:
    """Replace ``path`` atomically, keeping its permissions (the file holds a password)."""
    mode = path.stat().st_mode & 0o777
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".env.")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv: list[str]) -> int:
    """Run the sub-command named in ``argv``; the return value is the exit code."""
    if not argv or argv[0] not in {"status", "sqlite", "postgres"}:
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(argv[1] if len(argv) > 1 else ".env")
    exists = path.exists()
    lines = path.read_text().splitlines() if exists else []
    command = argv[0]
    if command == "status":
        text, warnings = status(lines)
        print(text)
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 0
    if command == "sqlite":
        if not exists:
            print("No .env: already on SQLite (the default).")
            return 0
        write(path, to_sqlite(lines))
        print("Switched to SQLite. Restart task serve / run task up to apply.")
        return 0
    try:
        updated = to_postgres(lines)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    write(path, updated)
    print("Switched to Postgres. Restart task serve / run task up to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
