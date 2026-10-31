#!/usr/bin/env python3
"""The live smoke test: one definition of the steps, used by CI and by the supabase-smoke skill.

It drives a running API over HTTP and proves the real path on the real database (Postgres behind
the Supabase pooler as the `lineup_app` role, so RLS, grants and the pooler are all in play):
create a team, a player and a saved lineup, read them back, generate a DOCX, then create, preview,
accept and revoke an invitation as a second user. Every row it writes is synthetic and carries
a `smoke-<unix time>` marker in its name.

Cleanup always runs, even when a step failed, and a final sweep deletes anything a crashed earlier
run left behind: teams named `smoke-<unix time> ...` that are more than an hour old. The sweep
works because both users are the stable ids `scripts/smoke_auth.py` issues tokens for.

Exit code 0 means every step passed; 1 means a step or a cleanup failed. The tokens and the
invite code are never printed. Standard library only, so it runs anywhere Python does:

    python3 scripts/smoke_live.py --base-url http://127.0.0.1:8000 \\
        --token-file /tmp/smoke.jwt --second-token-file /tmp/smoke2.jwt
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

MARKER_PREFIX = "smoke-"
SWEEP_AFTER_SECONDS = 3600
INVITER_NAME = "Smoke Owner"  # the name scripts/smoke_auth.py puts in its tokens
DOCX_TYPE = "wordprocessingml"
_MARKER = re.compile(rf"^{MARKER_PREFIX}(\d+)(?:\s|$)")


class SmokeFailure(Exception):
    """A step did not behave as expected. The message says which step and what came back."""


@dataclass
class Reply:
    """What the API answered: status, headers (lower-cased names) and the raw body."""

    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def json(self):
        """The body parsed as JSON; `SmokeFailure` when it is not JSON."""
        try:
            return json.loads(self.body)
        except ValueError as error:
            raise SmokeFailure(f"expected JSON, got status {self.status}") from error


# (method, path, token or None, JSON body or None) -> Reply
Transport = Callable[[str, str, str | None, dict | None], Reply]


def urllib_transport(base_url: str, timeout: float = 130) -> Transport:
    """A transport that talks to `base_url` over HTTP(S) with `urllib`.

    The timeout is long because the first request after a deploy may wake a cold machine. A
    connection error is returned as status 0 rather than raised, so a step fails normally and
    the cleanup still runs. Raises `ValueError` for a base URL that is not http(s), since `urllib` would also open
    `file:` URLs.
    """
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("--base-url must start with http:// or https://")
    base = base_url.rstrip("/")

    def send(method: str, path: str, token: str | None, body: dict | None) -> Reply:
        headers = {"accept": "application/json"}
        data = None
        if token:
            headers["authorization"] = f"Bearer {token}"
        if body is not None:
            data = json.dumps(body).encode()
            headers["content-type"] = "application/json"
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return Reply(
                    response.status,
                    {k.lower(): v for k, v in response.headers.items()},
                    response.read(),
                )
        except urllib.error.HTTPError as error:
            return Reply(
                error.code,
                {k.lower(): v for k, v in error.headers.items()},
                error.read(),
            )
        except (
            OSError
        ):  # refused, DNS, timeout: status 0, so the step fails and cleanup still runs
            return Reply(0)

    return send


def marker_age_seconds(name: str, now: float) -> float | None:
    """How old the `smoke-<unix time>` marker at the start of `name` is, or `None` if it has none."""
    match = _MARKER.match(name)
    return now - int(match.group(1)) if match else None


class Smoke:
    """Runs the steps against one API as two users and cleans up after itself."""

    def __init__(
        self,
        send: Transport,
        owner_token: str,
        member_token: str,
        marker: str,
        log: Callable[[str], None] = print,
    ) -> None:
        """`send` is the transport; the two tokens belong to different users (the owner creates
        everything, the member accepts the invitation); `marker` names every row (`smoke-<time>`)."""
        self.send = send
        self.owner = owner_token
        self.member = member_token
        self.marker = marker
        self.log = log
        self.team_id = self.player_id = self.lineup_id = self.member_id = None

    def call(
        self,
        step: str,
        method: str,
        path: str,
        status: int,
        who: str | None = "owner",
        body: dict | None = None,
    ) -> Reply:
        """Send one request as `who` (`owner`, `member` or `None` for anonymous), check the
        status, log the step and return the reply. Raises `SmokeFailure` on any other status."""
        token = {"owner": self.owner, "member": self.member, None: None}[who]
        reply = self.send(method, path, token, body)
        if reply.status != status:
            raise SmokeFailure(f"{step}: expected {status}, got {reply.status}")
        self.log(f"ok   {step} ({reply.status})")
        return reply

    @staticmethod
    def expect(step: str, condition: bool, detail: str) -> None:
        """Fail the step with `detail` unless `condition` holds."""
        if not condition:
            raise SmokeFailure(f"{step}: {detail}")

    def run(self) -> None:
        """The steps, in order. Raises `SmokeFailure` at the first one that goes wrong; call
        `cleanup` afterwards either way."""
        m = self.marker
        self.call("anonymous request is refused", "GET", "/teams", 401, who=None)

        team = self.call(
            "create team", "POST", "/teams", 201, body={"name": f"{m} team"}
        ).json()
        self.team_id = team["id"]
        player = self.call(
            "create player",
            "POST",
            "/players",
            201,
            body={
                "name": f"{m} player",
                "nssz_number": "SMOKE1",
                "team_id": self.team_id,
            },
        ).json()
        self.player_id = player["id"]
        lineup = self.call(
            "save lineup",
            "POST",
            "/lineups/saved",
            201,
            body={
                "team_id": self.team_id,
                "source_team_id": self.team_id,
                "opponent_name": f"{m} opponent",
                "division": "OB II.",
                "cap": "Fehér",
                "date": "2026. 01. 01.",
                "coach": "Smoke Coach",
                "players": [{"source_player_id": self.player_id, "cap_number": 1}],
            },
        ).json()
        self.lineup_id = lineup["id"]

        saved = self.call(
            "read lineup back", "GET", f"/lineups/saved/{self.lineup_id}", 200
        ).json()
        self.expect(
            "read lineup back",
            saved["team_name"] == f"{m} team"
            and [p["name"] for p in saved["players"]] == [f"{m} player"],
            "the frozen team or player name is wrong",
        )

        docx = self.call(
            "generate DOCX",
            "POST",
            f"/lineups/saved/{self.lineup_id}/generate?format=docx",
            200,
        )
        self.expect(
            "generate DOCX",
            DOCX_TYPE in docx.headers.get("content-type", "")
            and docx.body[:2] == b"PK",
            "not a DOCX document",
        )
        self.expect(
            "generate DOCX",
            "no-store" in docx.headers.get("cache-control", ""),
            "the file is not sent with Cache-Control: no-store",
        )
        self.call("search the opponent pool", "GET", f"/teams/pool?search={m}", 200)

        self.invitations()

    def invitations(self) -> None:
        """Create, preview, accept (twice) and revoke an invite link, with the permission checks
        around it. Needs the team from `run`."""
        team = f"/teams/{self.team_id}"
        invite = self.call(
            "create invitation",
            "POST",
            f"{team}/invitations",
            201,
            body={"expires_in_hours": 2},
        ).json()
        code, invitation_id = invite["code"], invite["id"]  # never logged

        preview = self.call(
            "preview without a token", "GET", f"/invitations/{code}", 200, who=None
        ).json()
        self.expect(
            "preview without a token",
            preview["team_name"] == f"{self.marker} team"
            and preview["invited_by_name"] == INVITER_NAME,
            "the preview shows the wrong team or inviter",
        )
        self.call(
            "non-member cannot invite", "POST", f"{team}/invitations", 404, who="member"
        )
        for step in ("accept the invitation", "accepting again changes nothing"):
            accepted = self.call(
                step, "POST", f"/invitations/{code}/accept", 200, who="member"
            ).json()
            self.expect(
                step, accepted["role"] == "member", "joined with the wrong role"
            )

        members = self.call("list members", "GET", f"{team}/members", 200).json()
        self.expect(
            "list members",
            sorted(row["role"] for row in members) == ["member", "owner"],
            "expected exactly one owner and one member",
        )
        others = [row["user_id"] for row in members if not row["is_you"]]
        self.member_id = others[0] if len(others) == 1 else None
        self.expect("list members", self.member_id is not None, "no second member")

        self.call(
            "member cannot invite", "POST", f"{team}/invitations", 403, who="member"
        )
        listed = self.call("list invitations", "GET", f"{team}/invitations", 200).json()
        self.expect(
            "list invitations",
            len(listed) == 1 and all("code" not in row for row in listed),
            "expected one link, and no code in the list",
        )
        self.call(
            "revoke the invitation",
            "DELETE",
            f"{team}/invitations/{invitation_id}",
            204,
        )
        self.call(
            "a revoked link is gone", "GET", f"/invitations/{code}", 410, who=None
        )

    def cleanup(self) -> list[str]:
        """Delete what `run` created, in the order the API allows (member, lineup, player, team).

        Never raises: it tries every deletion and returns the problems, so one failure does not
        leave the rest behind. A 404 counts as fine (it was never created or is already gone).
        """
        problems = []
        steps = [
            (
                "remove member",
                f"/teams/{self.team_id}/members/{self.member_id}",
                self.member_id,
            ),
            ("delete lineup", f"/lineups/saved/{self.lineup_id}", self.lineup_id),
            ("delete player", f"/players/{self.player_id}", self.player_id),
            ("delete team", f"/teams/{self.team_id}", self.team_id),
        ]
        for step, path, created in steps:
            if created is None:
                continue
            reply = self.send("DELETE", path, self.owner, None)
            if reply.status in (200, 204, 404):
                self.log(f"ok   cleanup: {step} ({reply.status})")
            else:
                problems.append(f"cleanup: {step} answered {reply.status}")
        return problems

    def _pages(self, path: str) -> list[dict]:
        """Every item of a paginated list endpoint as the owner (`limit` is capped at 200)."""
        items: list[dict] = []
        while True:
            sep = "&" if "?" in path else "?"
            reply = self.send(
                "GET", f"{path}{sep}limit=200&offset={len(items)}", self.owner, None
            )
            if reply.status != 200:
                raise SmokeFailure(f"list {path}: got {reply.status}")
            page = reply.json()
            items += page["items"]
            if not page["items"] or len(items) >= page["total"]:
                return items

    def sweep(self, now: float) -> list[str]:
        """Delete leftovers of crashed runs: the owner's teams marked `smoke-<time>` that are
        older than `SWEEP_AFTER_SECONDS`, with their lineups, players and members.

        Works only because the owner is a stable user. Never raises; returns the problems.
        """
        problems = []
        try:
            teams = self._pages("/teams")
        except SmokeFailure as error:
            return [f"sweep: {error}"]
        for team in teams:
            age = marker_age_seconds(team["name"], now)
            if age is None or age < SWEEP_AFTER_SECONDS or team["role"] != "owner":
                continue
            self.log(f"sweep: removing old team '{team['name'].split(' ')[0]}'")
            try:
                tid = team["id"]
                for lineup in self._pages(f"/lineups/saved?team_id={tid}"):
                    self._must_delete(f"/lineups/saved/{lineup['id']}")
                for player in self._pages(f"/players?team_id={tid}"):
                    self._must_delete(f"/players/{player['id']}")
                self._must_delete(f"/teams/{tid}")
            except SmokeFailure as error:
                problems.append(f"sweep: {error}")
        return problems

    def _must_delete(self, path: str) -> None:
        """DELETE as the owner; `SmokeFailure` unless it is 200, 204 or already gone."""
        status = self.send("DELETE", path, self.owner, None).status
        if status not in (200, 204, 404):
            raise SmokeFailure(f"DELETE {path.split('/')[1]} answered {status}")


def run_all(
    send: Transport,
    owner_token: str,
    member_token: str,
    now: float,
    log: Callable[[str], None] = print,
) -> bool:
    """Run the steps, always clean up, always sweep. Returns True when nothing went wrong."""
    smoke = Smoke(send, owner_token, member_token, f"{MARKER_PREFIX}{int(now)}", log)
    problems: list[str] = []
    try:
        smoke.run()
    except SmokeFailure as error:
        problems.append(str(error))
    problems += smoke.cleanup()
    problems += smoke.sweep(now)
    for problem in problems:
        log(f"FAIL {problem}")
    log("smoke test passed" if not problems else f"smoke test FAILED ({len(problems)})")
    return not problems


def main(argv: list[str] | None = None) -> int:
    """Read the token files, run the smoke test against `--base-url`, return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--second-token-file", required=True)
    args = parser.parse_args(argv)
    with open(args.token_file) as owner, open(args.second_token_file) as member:
        tokens = owner.read().strip(), member.read().strip()
    ok = run_all(urllib_transport(args.base_url), *tokens, now=time.time())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
