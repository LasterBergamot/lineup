"""The live smoke script (scripts/smoke_live.py) is the one definition of the steps that CI and the
supabase-smoke skill share. These tests run it against the real app on in-memory SQLite, so a
change to a route that would break the script breaks here first, and they prove the two promises
that matter: it fails loudly, and it always cleans up."""

import asyncio
import importlib.util
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import app
from lineup.auth.dependencies import get_current_display_name, get_current_user_id

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_live.py"
spec = importlib.util.spec_from_file_location("smoke_live", SCRIPT)
smoke_live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke_live)

USERS = {"owner-token": uuid.uuid4(), "member-token": uuid.uuid4()}
NOW = 1_800_000_000.0


@pytest.fixture
def two_users(async_client):
    """Sign requests in by their bearer token ("owner-token" / "member-token"), like the real
    verifier would, and answer 401 without one. Replaces the single-user override of
    `async_client`."""
    bearer = HTTPBearer(auto_error=False)

    def user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or credentials.credentials not in USERS:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return USERS[credentials.credentials]

    app.dependency_overrides[get_current_user_id] = user
    app.dependency_overrides[get_current_display_name] = lambda: smoke_live.INVITER_NAME
    return async_client


def bridge(client, loop, intercept=None):
    """A blocking transport for the script that sends through the async test client.

    The script is synchronous (it uses `urllib` in real life), so it runs in a worker thread and
    each request is handed to the event loop. `intercept(method, path)` may return a `Reply` to
    play a broken API.
    """

    def send(method, path, token, body):
        if intercept and (fake := intercept(method, path)):
            return fake
        headers = {"authorization": f"Bearer {token}"} if token else {}
        response = asyncio.run_coroutine_threadsafe(
            client.request(method, path, json=body, headers=headers), loop
        ).result()
        return smoke_live.Reply(
            response.status_code,
            {k.lower(): v for k, v in response.headers.items()},
            response.content,
        )

    return send


async def run_script(client, intercept=None):
    """Run the whole script in a worker thread; returns `(passed, log lines)`."""
    log: list[str] = []
    send = bridge(client, asyncio.get_running_loop(), intercept)
    passed = await asyncio.to_thread(
        smoke_live.run_all, send, "owner-token", "member-token", NOW, log.append
    )
    return passed, log


async def teams_of_owner(client):
    response = await client.get(
        "/teams", headers={"authorization": "Bearer owner-token"}
    )
    return response.json()["items"]


async def test_every_step_passes_and_nothing_is_left_behind(two_users):
    passed, log = await run_script(two_users)
    assert passed, log
    assert log[-1] == "smoke test passed"
    assert any("generate DOCX" in line for line in log)
    assert any("a revoked link is gone" in line for line in log)
    assert await teams_of_owner(two_users) == []


async def test_the_log_never_contains_a_token_or_an_invite_code(two_users):
    _, log = await run_script(two_users)
    assert not any("token" in line and "Bearer" in line for line in log)
    assert not any(len(word) > 40 for line in log for word in line.split())


async def test_a_broken_route_fails_the_run_but_still_cleans_up(two_users):
    def generate_is_broken(method, path):
        if path.endswith("/generate?format=docx"):
            return smoke_live.Reply(500)

    passed, log = await run_script(two_users, generate_is_broken)
    assert not passed
    assert "FAIL generate DOCX: expected 200, got 500" in log
    assert log[-1] == "smoke test FAILED (1)"
    assert await teams_of_owner(two_users) == []


async def test_a_failure_in_the_invitation_steps_removes_the_joined_member(two_users):
    def revoke_is_broken(method, path):
        if method == "DELETE" and "/invitations/" in path:
            return smoke_live.Reply(500)

    passed, _ = await run_script(two_users, revoke_is_broken)
    assert not passed
    assert await teams_of_owner(two_users) == []


async def test_an_unreachable_api_fails_without_raising(two_users):
    passed, log = await run_script(two_users, lambda method, path: smoke_live.Reply(0))
    assert not passed
    assert "FAIL anonymous request is refused: expected 401, got 0" in log


async def test_a_cleanup_that_is_refused_is_reported(two_users):
    def team_delete_refused(method, path):
        if method == "DELETE" and path.startswith("/teams/") and "/" not in path[7:]:
            return smoke_live.Reply(500)

    passed, log = await run_script(two_users, team_delete_refused)
    assert not passed
    assert "FAIL cleanup: delete team answered 500" in log


async def test_the_sweep_removes_old_smoke_teams_only(two_users):
    headers = {"authorization": "Bearer owner-token"}
    old = int(NOW) - 2 * 3600
    recent = int(NOW) - 60
    ids = {}
    for name in (f"smoke-{old} team", f"smoke-{recent} team", "SZVTK"):
        response = await two_users.post("/teams", json={"name": name}, headers=headers)
        ids[name] = response.json()["id"]
    old_team = ids[f"smoke-{old} team"]
    player = await two_users.post(
        "/players",
        json={"name": "smoke-p", "nssz_number": "SMOKE1", "team_id": old_team},
        headers=headers,
    )
    await two_users.post(
        "/lineups/saved",
        json={
            "team_id": old_team,
            "source_team_id": old_team,
            "opponent_name": "smoke-o",
            "division": "OB II.",
            "cap": "Fehér",
            "date": "2026. 01. 01.",
            "coach": "Smoke Coach",
            "players": [{"source_player_id": player.json()["id"], "cap_number": 1}],
        },
        headers=headers,
    )

    passed, log = await run_script(two_users)

    assert passed, log
    assert f"sweep: removing old team 'smoke-{old}'" in log
    names = sorted(team["name"] for team in await teams_of_owner(two_users))
    assert names == ["SZVTK", f"smoke-{recent} team"]


async def test_a_sweep_that_cannot_delete_reports_it(two_users):
    headers = {"authorization": "Bearer owner-token"}
    name = f"smoke-{int(NOW) - 2 * 3600} team"
    await two_users.post("/teams", json={"name": name}, headers=headers)

    def refuse_team_delete(method, path):
        if method == "DELETE" and path.startswith("/teams/") and "/" not in path[7:]:
            return smoke_live.Reply(500)

    passed, log = await run_script(two_users, refuse_team_delete)
    assert not passed
    assert "FAIL sweep: DELETE teams answered 500" in log


async def test_a_sweep_that_cannot_list_reports_it(two_users):
    def teams_list_broken(method, path):
        if method == "GET" and path.startswith("/teams?limit="):
            return smoke_live.Reply(500)

    passed, log = await run_script(two_users, teams_list_broken)
    assert not passed
    assert "FAIL sweep: list /teams: got 500" in log


def test_marker_age():
    assert smoke_live.marker_age_seconds("smoke-1000 team", 4600) == 3600
    assert smoke_live.marker_age_seconds("smoke-1000", 1001) == 1
    for name in ("SZVTK", "smoke-abc team", "smoke-1000x", "my smoke-1000 team"):
        assert smoke_live.marker_age_seconds(name, 5000) is None


# ── the real HTTP transport and the command line ──────────────────────────────


class Stub(BaseHTTPRequestHandler):
    """Records what it received; answers 200 JSON on /ok, 404 JSON elsewhere."""

    seen: list[tuple[str, str, str | None, bytes]] = []

    def _answer(self):
        length = int(self.headers.get("content-length") or 0)
        Stub.seen.append(
            (
                self.command,
                self.path,
                self.headers.get("authorization"),
                self.rfile.read(length),
            )
        )
        status = 200 if self.path == "/ok" else 404
        body = b'{"hello": "world"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = _answer

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture
def stub_url():
    Stub.seen = []
    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def test_the_transport_sends_the_token_and_body_and_reads_errors(stub_url):
    send = smoke_live.urllib_transport(stub_url)
    ok = send("POST", "/ok", "abc", {"a": 1})
    assert (ok.status, ok.json()) == (200, {"hello": "world"})
    assert ok.headers["content-type"] == "application/json"
    assert Stub.seen[0] == ("POST", "/ok", "Bearer abc", b'{"a": 1}')
    missing = send("GET", "/nope", None, None)
    assert missing.status == 404
    assert Stub.seen[1][2] is None


def test_the_transport_reports_an_unreachable_server_as_status_0():
    assert (
        smoke_live.urllib_transport("http://127.0.0.1:1")("GET", "/", None, None).status
        == 0
    )


def test_the_transport_refuses_non_http_urls():
    with pytest.raises(ValueError):
        smoke_live.urllib_transport("file:///etc/passwd")


def test_a_reply_that_is_not_json_is_a_failure():
    with pytest.raises(smoke_live.SmokeFailure):
        smoke_live.Reply(200, body=b"<html>").json()


@pytest.mark.parametrize("passed, code", [(True, 0), (False, 1)])
def test_main_reads_the_token_files_and_returns_the_exit_code(
    tmp_path, monkeypatch, passed, code
):
    (tmp_path / "a").write_text("owner\n")
    (tmp_path / "b").write_text("member\n")
    calls = []
    monkeypatch.setattr(smoke_live, "urllib_transport", lambda url: url)
    monkeypatch.setattr(
        smoke_live,
        "run_all",
        lambda send, a, b, now: calls.append((send, a, b)) or passed,
    )
    argv = [
        "--base-url",
        "http://x",
        "--token-file",
        str(tmp_path / "a"),
        "--second-token-file",
        str(tmp_path / "b"),
    ]
    assert smoke_live.main(argv) == code
    assert calls == [("http://x", "owner", "member")]
