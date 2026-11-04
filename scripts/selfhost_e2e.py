#!/usr/bin/env python3
"""End-to-end test of the self-hosted stack: real Auth, real Postgres, real PDF.

It builds and starts `selfhost/compose.yml` with the test overlay `selfhost/compose.test.yml` as the
Compose project `lineup-selfhost-test`, with a throw-away `.env` of generated secrets in a private
temp directory, and then checks, through the one published port (`http://localhost:8088`):

1. two users sign up with the stack's own Auth and get real ES256 access tokens;
2. the existing live smoke test (`scripts/smoke_live.py`, the single definition of those steps) passes
   against `/api` with those tokens;
3. `/auth/v1/admin/users` and `/auth/v1/signup` are 404 (only the allow-listed Auth paths are public),
   `/join/x` returns the app, `/api/docs` is 404;
4. `POST /api/lineups` with a token returns a real `application/pdf`, and a token signed by a
   different key (same `kid` and claims) is refused with 401;
5. nothing but the test overlay's web port is published on the host;
6. the operator tool `selfhost/lineup.sh` backs the stack up, a team is deleted, `lineup.sh restore`
   brings the team back, the token tables that backups leave out are empty after the restore, and
   signing in with the password works again.

Sign-up goes straight to the Auth container (from inside the `api` container, over the private
network) because the public allow-list deliberately has no `/signup`: a Google-only install needs none.

The `finally` block always runs `down -v` and deletes the temp directory. Tokens and passwords are
never printed. Standard library only (the key is made by `python -m lineup.auth.signing_key`, so run
this from `backend/` with its Python: `task selfhost:test` does). Exit code 0 means everything passed.
"""

import argparse
import datetime
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "lineup-selfhost-test"
BASE_URL = "http://localhost:8088"
COMPOSE_FILES = ("selfhost/compose.yml", "selfhost/compose.test.yml")
# The name smoke_live.py expects the inviter to have (its INVITER_NAME; a test keeps the two equal).
# Real Auth copies the sign-up `data` into the token's `user_metadata`, like Google sign-in does.
DISPLAY_NAME = "Smoke Owner"
UP_TIMEOUT_SECONDS = 600
REQUEST_TIMEOUT_SECONDS = 180
LINEUP_SH = ROOT / "selfhost" / "lineup.sh"
LINEUP_SH_TIMEOUT_SECONDS = 900

# Same data as the container e2e suite (backend/tests/test_pdf_conversion_e2e.py).
LINEUP_BODY = {
    "match": "SZVTK - Csongrád",
    "division": "OB II.",
    "team_name": "SZVTK",
    "cap": "Fehér",
    "date": "2024. 12. 21.",
    "coach": "Török András",
    "doctor": "Török András",
    "assistant_coach": "Török András",
    "team_leader": "Török András",
    "ball_thrower": "Török András",
    "players": [
        {
            "cap_number": i,
            "name": "Török András",
            "nssz_number": f"MVLSZ{123456788 + i}",
        }
        for i in range(1, 16)
    ],
}

# Runs inside the `api` container (python and PyJWT are there). Reads {"email", "password"} on stdin
# and prints Auth's sign-up answer: the password never appears on a command line.
SIGNUP_SCRIPT = (
    "import sys, urllib.request\n"
    "request = urllib.request.Request('http://auth:9999/signup', data=sys.stdin.buffer.read(),"
    " headers={'content-type': 'application/json'})\n"
    "print(urllib.request.urlopen(request, timeout=30).read().decode())\n"
)

# Runs inside the `api` container: password sign-in against Auth, credentials on stdin.
SIGNIN_SCRIPT = (
    "import sys, urllib.request\n"
    "request = urllib.request.Request('http://auth:9999/token?grant_type=password',"
    " data=sys.stdin.buffer.read(), headers={'content-type': 'application/json'})\n"
    "print(urllib.request.urlopen(request, timeout=30).read().decode())\n"
)

# Re-signs the token on stdin with a freshly generated key, keeping its header (so the same `kid`)
# and claims: the verifier must find the real key by `kid` and reject the signature.
FORGE_SCRIPT = (
    "import sys, jwt\n"
    "from cryptography.hazmat.primitives.asymmetric import ec\n"
    "token = sys.stdin.read().strip()\n"
    "kid = jwt.get_unverified_header(token)['kid']\n"
    "claims = jwt.decode(token, options={'verify_signature': False})\n"
    "key = ec.generate_private_key(ec.SECP256R1())\n"
    "print(jwt.encode(claims, key, algorithm='ES256', headers={'kid': kid}))\n"
)


class E2EFailure(Exception):
    """A check failed. The message says which one and never contains a token or a password."""


def expect(condition: bool, message: str) -> None:
    """Raise `E2EFailure(message)` unless `condition` holds."""
    if not condition:
        raise E2EFailure(message)


def generate_env(
    jwt_keys: str,
    public_url: str = BASE_URL,
    token_hex: Callable[[int], str] = secrets.token_hex,
    backup_dir: str | None = None,
) -> dict[str, str]:
    """The values of a throw-away `selfhost/.env`: generated secrets, fake Google values, no tunnel.

    `jwt_keys` is the JSON array printed by `lineup.auth.signing_key`. Every password is hex, so it
    is URL-safe where compose puts it into a connection URL. `AUTH_EMAIL_ENABLED=true` is what lets the
    test get tokens without Google. `backup_dir`, when given, is where the `backup` service writes.
    """
    values = {
        "LINEUP_VERSION": "selfhost-test",
        "PUBLIC_URL": public_url,
        "POSTGRES_PASSWORD": token_hex(16),
        "AUTH_DB_PASSWORD": token_hex(16),
        "LINEUP_APP_PASSWORD": token_hex(16),
        "AUTH_JWT_SECRET": token_hex(32),
        "AUTH_JWT_KEYS": jwt_keys,
        "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        "GOOGLE_SECRET": "test-google-secret",
        "AUTH_EMAIL_ENABLED": "true",
    }
    if backup_dir:
        values["BACKUP_DIR"] = backup_dir
    return values


def render_env(values: dict[str, str]) -> str:
    """`values` as `.env` text; `AUTH_JWT_KEYS` is single-quoted because it is JSON.

    Raises `ValueError` if a value holds a single quote or a newline, which `.env` could not carry.
    """
    lines = []
    for name, value in values.items():
        if "'" in value or "\n" in value:
            raise ValueError(f"{name} cannot be written to an .env file")
        lines.append(
            f"{name}='{value}'" if name == "AUTH_JWT_KEYS" else f"{name}={value}"
        )
    return "\n".join(lines) + "\n"


def write_private(path: Path, text: str) -> None:
    """Write `text` to a new file that only the owner can read (mode 600 from the start)."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(text)


def compose_command(env_file: Path, *args: str) -> list[str]:
    """The `docker compose` command line for the test stack plus `args`."""
    command = ["docker", "compose", "--env-file", str(env_file)]
    for name in COMPOSE_FILES:
        command += ["-f", str(ROOT / name)]
    return [*command, "-p", PROJECT, *args]


def access_token_from(body: str) -> str:
    """The access token in Auth's sign-up answer.

    Raises `E2EFailure` if the answer is not JSON or has no token. The answer is never put into the
    message: it may hold a token or an e-mail address.
    """
    try:
        token = json.loads(body).get("access_token")
    except (ValueError, AttributeError) as error:
        raise E2EFailure("sign-up did not answer with JSON") from error
    expect(
        isinstance(token, str) and token.count(".") == 2, "sign-up gave no access token"
    )
    return token


def published_ports(ps_output: str) -> dict[str, list[str]]:
    """Which services publish a port, from `docker compose ps --format json` (one object per line).

    Returns `{service: ["127.0.0.1:8088->8080", ...]}` for services with at least one published port.
    """
    published: dict[str, list[str]] = {}
    for line in ps_output.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ports = [
            f"{port['URL']}:{port['PublishedPort']}->{port['TargetPort']}"
            for port in row.get("Publishers") or []
            if port.get("PublishedPort")
        ]
        if ports:
            published.setdefault(row["Service"], []).extend(sorted(set(ports)))
    return published


def is_pdf(headers: dict[str, str], body: bytes) -> bool:
    """True when the reply declares `application/pdf` and the body starts like a PDF file."""
    return headers.get("content-type", "").split(";")[
        0
    ].strip() == "application/pdf" and body.startswith(b"%PDF")


def http(
    method: str, path: str, token: str | None = None, body: dict | None = None
) -> tuple[int, dict[str, str], bytes]:
    """One request to the stack's published port: (status, lower-cased headers, body).

    A connection error gives status 0 so the caller's check fails normally. Only `BASE_URL` is used,
    which is http://localhost.
    """
    headers = {}
    data = None
    if token:
        headers["authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    request = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method=method
    )  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as reply:  # noqa: S310
            return (
                reply.status,
                {k.lower(): v for k, v in reply.headers.items()},
                reply.read(),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            {k.lower(): v for k, v in error.headers.items()},
            error.read(),
        )
    except OSError:
        return 0, {}, b""


def run_compose(
    env_file: Path, *args: str, stdin: str | None = None
) -> subprocess.CompletedProcess:
    """Run a compose command; stdout is captured (it may hold tokens), stderr is left to the console."""
    return subprocess.run(  # noqa: S603
        compose_command(env_file, *args),
        input=stdin,
        stdout=subprocess.PIPE,
        text=True,
        check=False,
        cwd=ROOT,
    )


def test_email(number: int) -> str:
    """The e-mail address of test user `number`."""
    return f"selfhost-test-{number}@example.com"


def sign_up(env_file: Path, number: int, password: str | None = None) -> str:
    """Create user `number` in the stack's Auth and return its access token.

    `password` is generated unless given (the backup check needs to sign in again later).
    """
    credentials = json.dumps(
        {
            "email": test_email(number),
            "password": password or secrets.token_urlsafe(24),
            "data": {"full_name": DISPLAY_NAME},
        }
    )
    result = run_compose(
        env_file, "exec", "-T", "api", "python", "-c", SIGNUP_SCRIPT, stdin=credentials
    )
    expect(result.returncode == 0, f"sign-up {number} failed")
    return access_token_from(result.stdout)


def sign_in(env_file: Path, number: int, password: str) -> str:
    """Sign user `number` in with its password through the stack's Auth; return the access token."""
    credentials = json.dumps({"email": test_email(number), "password": password})
    result = run_compose(
        env_file, "exec", "-T", "api", "python", "-c", SIGNIN_SCRIPT, stdin=credentials
    )
    expect(result.returncode == 0, f"sign-in {number} failed")
    return access_token_from(result.stdout)


def forge_token(env_file: Path, token: str) -> str:
    """A token with `token`'s header and claims, signed by a different, freshly made key."""
    result = run_compose(
        env_file, "exec", "-T", "api", "python", "-c", FORGE_SCRIPT, stdin=token
    )
    expect(result.returncode == 0, "could not forge a token")
    forged = result.stdout.strip()
    expect(forged.count(".") == 2, "could not forge a token")
    return forged


def lineup_sh_environment(env_file: Path) -> dict[str, str]:
    """The environment that points `lineup.sh` at the test stack instead of a real install.

    These are the script's documented test settings: the `.env` file, the two compose files, the
    Compose project, and English messages (so the output is the same on every machine).
    """
    return {
        **os.environ,
        "LINEUP_ENV_FILE": str(env_file),
        "LINEUP_COMPOSE_FILES": " ".join(str(ROOT / name) for name in COMPOSE_FILES),
        "LINEUP_PROJECT": PROJECT,
        "LINEUP_LANG": "en",
    }


def run_lineup_sh(env_file: Path, *args: str) -> int:
    """Run `selfhost/lineup.sh <args>` against the test stack with no input; return its exit code.

    Its output (it never holds a secret) goes to the console, so a failure explains itself.
    """
    return subprocess.run(  # noqa: S603
        ["bash", str(LINEUP_SH), *args],
        env=lineup_sh_environment(env_file),
        stdin=subprocess.DEVNULL,
        check=False,
        cwd=ROOT,
        timeout=LINEUP_SH_TIMEOUT_SECONDS,
    ).returncode


def team_names(token: str) -> list[str]:
    """The names of the teams the token's user belongs to (first page, up to 200)."""
    status, _, body = http("GET", "/api/teams?limit=200", token)
    expect(status == 200, f"GET /api/teams answered {status}, expected 200")
    return [team["name"] for team in json.loads(body)["items"]]


def count_rows(env_file: Path, table: str) -> int:
    """How many rows `table` (an `auth` table) holds, asked of the database as its owner."""
    result = run_compose(
        env_file,
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "postgres",
        "-d",
        "auth",
        "-tAc",
        f"select count(*) from auth.{table}",
    )
    expect(result.returncode == 0, f"could not count the rows of {table}")
    return int(result.stdout.strip())


def check_backup_and_restore(
    env_file: Path, owner: str, owner_password: str, member_number: int = 1
) -> None:
    """Back up with `lineup.sh`, lose a team, restore, and check the data and sign-in are back.

    Raises `E2EFailure`. The token tables that backups leave out (`refresh_tokens` here) must hold
    rows before and none after the restore, which proves both the exclusion and that the restore
    really replaced the `auth` database.
    """
    team_name = f"backup-test-{secrets.token_hex(4)}"
    print("creating a team, then backing up with lineup.sh")
    status, _, body = http("POST", "/api/teams", owner, {"name": team_name})
    expect(status == 201, f"creating the team answered {status}, expected 201")
    team_id = json.loads(body)["id"]
    expect(team_name in team_names(owner), "the new team is not listed")
    expect(count_rows(env_file, "refresh_tokens") > 0, "no sign-in rows to leave out")
    expect(run_lineup_sh(env_file, "backup") == 0, "lineup.sh backup failed")

    print("deleting the team")
    status = http("DELETE", f"/api/teams/{team_id}", owner)[0]
    expect(status in (200, 204), f"deleting the team answered {status}")
    expect(team_name not in team_names(owner), "the team is still listed")

    print("restoring today's backup with lineup.sh")
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    code = run_lineup_sh(env_file, "restore", "--date", today, "--yes-restore")
    expect(code == 0, "lineup.sh restore failed")
    expect(
        count_rows(env_file, "refresh_tokens") == 0,
        "sign-in tokens were restored, but backups must leave them out",
    )
    expect(
        run_lineup_sh(env_file, "restore", "--date", "1999-01-01", "--yes-restore") != 0,
        "restoring a date that has no backup did not fail",
    )

    print("signing in again with the password")
    fresh = sign_in(env_file, member_number, owner_password)
    expect(team_name in team_names(fresh), "the team did not come back after the restore")


def check_stack(env_file: Path, tmp: Path) -> None:
    """Every check of the module docstring against the running stack. Raises `E2EFailure`."""
    print("signing two users up through the stack's own Auth")
    owner_password = secrets.token_urlsafe(24)
    owner, member = sign_up(env_file, 1, owner_password), sign_up(env_file, 2)
    owner_file, member_file = tmp / "owner.jwt", tmp / "member.jwt"
    write_private(owner_file, owner)
    write_private(member_file, member)

    print("running scripts/smoke_live.py against /api")
    smoke = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(ROOT / "scripts" / "smoke_live.py"),
            "--base-url",
            f"{BASE_URL}/api",
            "--token-file",
            str(owner_file),
            "--second-token-file",
            str(member_file),
        ],
        check=False,
    )
    expect(smoke.returncode == 0, "the live smoke test failed")

    print("checking what is public and what is not")
    for method, path in (
        ("GET", "/auth/v1/admin/users"),
        ("POST", "/auth/v1/signup"),
        ("GET", "/api/docs"),
    ):
        status = http(method, path)[0]
        expect(status == 404, f"{method} {path} answered {status}, expected 404")
    status, headers, body = http("GET", "/join/x")
    expect(
        status == 200
        and "text/html" in headers.get("content-type", "")
        and b'id="root"' in body,
        f"/join/x did not return the app (status {status})",
    )
    status = http("GET", "/auth/v1/.well-known/jwks.json")[0]
    expect(status == 200, f"the signing keys are not public (status {status})")

    print("generating a PDF with a real token")
    status, headers, body = http("POST", "/api/lineups", owner, LINEUP_BODY)
    expect(
        status == 200 and is_pdf(headers, body),
        f"POST /api/lineups did not return a PDF (status {status})",
    )
    status = http("POST", "/api/lineups", None, LINEUP_BODY)[0]
    expect(
        status == 401,
        f"POST /api/lineups without a token answered {status}, expected 401",
    )
    status = http("POST", "/api/lineups", forge_token(env_file, owner), LINEUP_BODY)[0]
    expect(
        status == 401, f"a token signed by another key answered {status}, expected 401"
    )

    print("checking that only the web port is published")
    ps = run_compose(env_file, "ps", "--format", "json")
    expect(ps.returncode == 0, "docker compose ps failed")
    expect(
        published_ports(ps.stdout) == {"web": ["127.0.0.1:8088->8080"]},
        "the stack publishes something besides the test overlay's web port",
    )

    check_backup_and_restore(env_file, owner, owner_password)


def release_backup_folder(env_file: Path) -> None:
    """Hand the backup folder back to the current user so the temp directory can be deleted.

    `lineup.sh` gives the folder to user 999 (the backup service's user) with mode 700, so even its
    owner of the temp directory cannot delete it. One throw-away container with the few capabilities
    this needs does the `chown`. Best effort: a failure leaves a folder in the temp directory.
    """
    run_compose(
        env_file,
        "run",
        "--rm",
        "-T",
        "--no-deps",
        "--user",
        "0",
        "--cap-add",
        "CHOWN",
        "--cap-add",
        "DAC_OVERRIDE",
        "--cap-add",
        "FOWNER",
        "--entrypoint",
        "chown",
        "backup",
        "-R",
        f"{os.getuid()}:{os.getgid()}",
        "/backups",
    )


def main(argv: list[str] | None = None) -> int:
    """Run the whole test; return 0 on success and 1 on any failure. Always cleans up."""
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args(argv)
    tmp = Path(tempfile.mkdtemp(prefix="lineup-selfhost-"))
    env_file = tmp / ".env"
    try:
        keys = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "lineup.auth.signing_key"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
            cwd=ROOT / "backend",
        ).stdout.strip()
        write_private(
            env_file, render_env(generate_env(keys, backup_dir=str(tmp / "backups")))
        )
        print("building and starting the stack (this builds three images)")
        up = run_compose(
            env_file,
            "up",
            "-d",
            "--build",
            "--wait",
            "--wait-timeout",
            str(UP_TIMEOUT_SECONDS),
        )
        expect(up.returncode == 0, "the stack did not become healthy")
        check_stack(env_file, tmp)
    except (E2EFailure, subprocess.CalledProcessError, OSError, ValueError) as error:
        print(
            f"FAILED: {error if isinstance(error, E2EFailure) else type(error).__name__}",
            file=sys.stderr,
        )
        return 1
    else:
        print("OK")
        return 0
    finally:
        if env_file.exists():
            release_backup_folder(env_file)
            subprocess.run(  # noqa: S603
                compose_command(env_file, "down", "-v", "--remove-orphans"),
                check=False,
                cwd=ROOT,
            )
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
