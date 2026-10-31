"""Guards on deployment files that protect secrets in URLs and point invite links at the app."""

import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_uvicorn_runs_without_its_access_log():
    """Invite codes are URL path segments (`/invitations/<code>`); the access log would print
    every one of them, with the client IP, into the platform logs (requirements S4/S8)."""
    cmd = next(
        line
        for line in (BACKEND / "Dockerfile").read_text().splitlines()
        if line.startswith("CMD")
    )
    assert '"uvicorn"' in cmd
    assert '"--no-access-log"' in cmd


def test_fly_points_invite_links_at_the_pages_site():
    env = tomllib.loads((BACKEND / "fly.toml").read_text())["env"]
    assert env["APP_BASE_URL"].startswith("https://")
    assert not env["APP_BASE_URL"].endswith("/")
