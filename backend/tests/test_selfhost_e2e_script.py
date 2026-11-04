"""The helpers of scripts/selfhost_e2e.py, the end-to-end test of the self-hosted stack.

The script itself needs Docker and takes minutes (`task selfhost:test`). These tests cover the parts
that can go wrong without it: the throw-away `.env`, the private file mode, how answers are read, the
published-port check and the guarantee that cleanup runs and nothing secret is printed.
"""

import importlib.util
import json
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "selfhost_e2e.py"
spec = importlib.util.spec_from_file_location("selfhost_e2e", SCRIPT)
e2e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e2e)

SMOKE = Path(__file__).resolve().parents[2] / "scripts" / "smoke_live.py"
smoke_spec = importlib.util.spec_from_file_location("smoke_live", SMOKE)
smoke_live = importlib.util.module_from_spec(smoke_spec)
smoke_spec.loader.exec_module(smoke_live)

KEYS = '[{"kty":"EC","d":"private-part"}]'
FAKE_JWT = "aaa.bbb.ccc"


class TestEnvFile:
    def test_secrets_are_generated_and_distinct(self):
        values = e2e.generate_env(KEYS)
        passwords = [
            values[k]
            for k in ("POSTGRES_PASSWORD", "AUTH_DB_PASSWORD", "LINEUP_APP_PASSWORD")
        ]
        assert len(set(passwords)) == 3
        assert all(len(p) == 32 and p.isalnum() for p in passwords)
        assert e2e.generate_env(KEYS) != values

    def test_it_points_at_localhost_with_fake_google_and_no_tunnel(self):
        values = e2e.generate_env(KEYS)
        assert values["PUBLIC_URL"] == "http://localhost:8088"
        assert values["AUTH_EMAIL_ENABLED"] == "true"
        assert "TUNNEL_TOKEN" not in values
        assert values["GOOGLE_CLIENT_ID"].startswith("test-")

    def test_every_variable_compose_requires_is_present(self):
        compose = (SCRIPT.parents[1] / "selfhost" / "compose.yml").read_text()
        import re

        required = set(re.findall(r"\$\{([A-Z_]+):\?\}", compose))
        assert required <= set(e2e.generate_env(KEYS))

    def test_the_key_json_is_single_quoted_and_the_rest_is_not(self):
        text = e2e.render_env({"A": "1", "AUTH_JWT_KEYS": KEYS})
        assert text == f"A=1\nAUTH_JWT_KEYS='{KEYS}'\n"

    @pytest.mark.parametrize("bad", ["it's", "two\nlines"])
    def test_a_value_an_env_file_cannot_carry_is_refused(self, bad):
        with pytest.raises(ValueError, match="cannot be written") as raised:
            e2e.render_env({"X": bad})
        assert bad not in str(raised.value)

    def test_the_file_is_private_from_the_start(self, tmp_path):
        path = tmp_path / ".env"
        e2e.write_private(path, "secret")
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert path.read_text() == "secret"
        with pytest.raises(FileExistsError):
            e2e.write_private(path, "again")


class TestComposeCommand:
    def test_it_uses_both_files_and_its_own_project(self, tmp_path):
        command = e2e.compose_command(tmp_path / ".env", "ps")
        assert command[:2] == ["docker", "compose"]
        assert command[command.index("--env-file") + 1] == str(tmp_path / ".env")
        files = [command[i + 1] for i, c in enumerate(command) if c == "-f"]
        assert [Path(f).relative_to(e2e.ROOT).as_posix() for f in files] == [
            "selfhost/compose.yml",
            "selfhost/compose.test.yml",
        ]
        assert command[command.index("-p") + 1] == "lineup-selfhost-test"
        assert command[-1] == "ps"


class TestReadingAnswers:
    def test_token_from_a_signup_answer(self):
        assert e2e.access_token_from(json.dumps({"access_token": FAKE_JWT})) == FAKE_JWT

    @pytest.mark.parametrize(
        "body",
        [
            "not json",
            "[]",
            json.dumps({"user": {}}),
            json.dumps({"access_token": "no-dots"}),
        ],
    )
    def test_a_bad_answer_fails_without_echoing_it(self, body):
        with pytest.raises(e2e.E2EFailure) as raised:
            e2e.access_token_from(body)
        assert body not in str(raised.value)

    def test_pdf_needs_the_type_and_the_magic_bytes(self):
        pdf = {"content-type": "application/pdf"}
        assert e2e.is_pdf(pdf, b"%PDF-1.7 ...")
        assert e2e.is_pdf({"content-type": "application/pdf; charset=binary"}, b"%PDF-")
        assert not e2e.is_pdf(pdf, b"<html>")
        assert not e2e.is_pdf({"content-type": "text/html"}, b"%PDF-")
        assert not e2e.is_pdf({}, b"%PDF-")

    def test_published_ports_ignores_unpublished_and_blank_lines(self):
        web = {
            "Service": "web",
            "Publishers": [
                {"URL": "127.0.0.1", "TargetPort": 8080, "PublishedPort": 8088},
                {"URL": "", "TargetPort": 443, "PublishedPort": 0},
            ],
        }
        db = {
            "Service": "db",
            "Publishers": [{"URL": "", "TargetPort": 5432, "PublishedPort": 0}],
        }
        idle = {"Service": "migrate", "Publishers": None}
        output = "\n".join(json.dumps(row) for row in (web, db, idle)) + "\n\n"
        assert e2e.published_ports(output) == {"web": ["127.0.0.1:8088->8080"]}

    def test_published_ports_sees_an_unexpected_port(self):
        row = {
            "Service": "db",
            "Publishers": [
                {"URL": "10.0.0.5", "TargetPort": 5432, "PublishedPort": 5432}
            ],
        }
        assert e2e.published_ports(json.dumps(row)) == {"db": ["10.0.0.5:5432->5432"]}


def test_expect_raises_only_when_the_condition_fails():
    e2e.expect(True, "never raised")
    with pytest.raises(e2e.E2EFailure, match="boom"):
        e2e.expect(False, "boom")


def test_the_sign_up_name_is_the_one_the_smoke_test_expects():
    assert e2e.DISPLAY_NAME == smoke_live.INVITER_NAME


def test_the_forged_token_script_keeps_the_kid_and_claims_but_not_the_key():
    """Run the in-container script here, where PyJWT and cryptography are installed."""
    import jwt
    from cryptography.hazmat.primitives.asymmetric import ec

    real_key = ec.generate_private_key(ec.SECP256R1())
    real = jwt.encode(
        {"sub": "u", "aud": "authenticated"},
        real_key,
        algorithm="ES256",
        headers={"kid": "k1"},
    )
    import sys

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", e2e.FORGE_SCRIPT],
        input=real,
        capture_output=True,
        text=True,
        check=True,
    )
    forged = result.stdout.strip()
    assert forged != real
    assert jwt.get_unverified_header(forged)["kid"] == "k1"
    assert jwt.decode(forged, options={"verify_signature": False}) == {
        "sub": "u",
        "aud": "authenticated",
    }
    jwt.decode(
        real, real_key.public_key(), algorithms=["ES256"], audience="authenticated"
    )
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            forged,
            real_key.public_key(),
            algorithms=["ES256"],
            audience="authenticated",
        )


class FakeProcess:
    def __init__(self, returncode=0, stdout=""):
        self.returncode, self.stdout = returncode, stdout


class TestSteps:
    def test_sign_up_sends_credentials_on_stdin_never_on_the_command_line(
        self, monkeypatch, tmp_path
    ):
        seen = {}

        def fake_run(env_file, *args, stdin=None):
            seen["args"], seen["stdin"] = args, stdin
            return FakeProcess(0, json.dumps({"access_token": FAKE_JWT}))

        monkeypatch.setattr(e2e, "run_compose", fake_run)
        assert e2e.sign_up(tmp_path / ".env", 3) == FAKE_JWT
        body = json.loads(seen["stdin"])
        assert body["email"] == "selfhost-test-3@example.com"
        assert body["data"] == {"full_name": e2e.DISPLAY_NAME}
        assert body["password"] not in " ".join(seen["args"])
        assert len(body["password"]) >= 24

    def test_sign_up_failure_is_reported(self, monkeypatch, tmp_path):
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: FakeProcess(1, ""))
        with pytest.raises(e2e.E2EFailure, match="sign-up 1 failed"):
            e2e.sign_up(tmp_path / ".env", 1)

    def test_forge_token(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            e2e, "run_compose", lambda *a, **k: FakeProcess(0, "x.y.z\n")
        )
        assert e2e.forge_token(tmp_path / ".env", FAKE_JWT) == "x.y.z"

    @pytest.mark.parametrize(
        "process", [FakeProcess(1, "x.y.z"), FakeProcess(0, "garbage")]
    )
    def test_forge_token_failure(self, monkeypatch, tmp_path, process):
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: process)
        with pytest.raises(e2e.E2EFailure, match="forge"):
            e2e.forge_token(tmp_path / ".env", FAKE_JWT)


class TestHttp:
    def test_a_refused_connection_is_status_zero(self, monkeypatch):
        def refuse(*args, **kwargs):
            raise OSError("refused")

        monkeypatch.setattr(e2e.urllib.request, "urlopen", refuse)
        assert e2e.http("GET", "/") == (0, {}, b"")

    def test_an_http_error_keeps_its_status_and_body(self, monkeypatch):
        import io
        import urllib.error

        def fail(*args, **kwargs):
            raise urllib.error.HTTPError(
                "u", 404, "nf", {"X-A": "b"}, io.BytesIO(b"gone")
            )

        monkeypatch.setattr(e2e.urllib.request, "urlopen", fail)
        assert e2e.http("GET", "/x") == (404, {"x-a": "b"}, b"gone")

    def test_a_reply_and_the_request_it_sent(self, monkeypatch):
        sent = {}

        class Reply:
            status = 200

            def __init__(self):
                self.headers = {"Content-Type": "application/pdf"}

            def read(self):
                return b"%PDF"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_open(request, timeout):
            sent["request"] = request
            return Reply()

        monkeypatch.setattr(e2e.urllib.request, "urlopen", fake_open)
        assert e2e.http("POST", "/api/lineups", FAKE_JWT, {"a": 1}) == (
            200,
            {"content-type": "application/pdf"},
            b"%PDF",
        )
        request = sent["request"]
        assert request.full_url == "http://localhost:8088/api/lineups"
        assert request.get_header("Authorization") == f"Bearer {FAKE_JWT}"
        assert json.loads(request.data) == {"a": 1}


class TestMain:
    @pytest.fixture
    def calls(self, monkeypatch):
        """Replace every outside effect; record the compose commands and the temp directory."""
        record = {"compose": [], "tmp": None}

        def fake_run(command, **kwargs):
            if command[:2] == ["docker", "compose"]:
                record["compose"].append(command)
                record["tmp"] = Path(command[command.index("--env-file") + 1]).parent
                record["env_existed"] = Path(
                    command[command.index("--env-file") + 1]
                ).exists()
                return subprocess.CompletedProcess(command, 0, "")
            return subprocess.CompletedProcess(command, 0, KEYS + "\n")

        monkeypatch.setattr(e2e.subprocess, "run", fake_run)
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: FakeProcess(0, ""))
        return record

    def test_success_runs_down_and_removes_the_temp_files(
        self, monkeypatch, calls, capsys
    ):
        monkeypatch.setattr(e2e, "check_stack", lambda env_file, tmp: None)
        assert e2e.main([]) == 0
        down = calls["compose"][-1]
        assert down[-3:] == ["down", "-v", "--remove-orphans"]
        assert calls["env_existed"]
        assert not calls["tmp"].exists()
        assert capsys.readouterr().out.rstrip().endswith("OK")

    def test_a_failure_still_cleans_up_and_prints_only_the_message(
        self, monkeypatch, calls, capsys
    ):
        def boom(env_file, tmp):
            raise e2e.E2EFailure("step X failed")

        monkeypatch.setattr(e2e, "check_stack", boom)
        assert e2e.main([]) == 1
        assert calls["compose"][-1][-3:] == ["down", "-v", "--remove-orphans"]
        assert not calls["tmp"].exists()
        assert "FAILED: step X failed" in capsys.readouterr().err

    def test_an_unexpected_error_prints_only_its_class(
        self, monkeypatch, calls, capsys
    ):
        def boom(env_file, tmp):
            raise OSError("path with secret-value")

        monkeypatch.setattr(e2e, "check_stack", boom)
        assert e2e.main([]) == 1
        err = capsys.readouterr().err
        assert "OSError" in err
        assert "secret-value" not in err

    def test_a_stack_that_never_gets_healthy_fails(self, monkeypatch, calls, capsys):
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: FakeProcess(1, ""))
        monkeypatch.setattr(
            e2e, "check_stack", lambda env_file, tmp: pytest.fail("must not run")
        )
        assert e2e.main([]) == 1
        assert "did not become healthy" in capsys.readouterr().err
        assert calls["compose"][-1][-3:] == ["down", "-v", "--remove-orphans"]


class TestBackupAndRestoreCheck:
    """The part of the test that backs up with lineup.sh, deletes a team, restores and signs in again."""

    def test_the_backup_folder_is_part_of_the_env_only_when_given(self):
        assert "BACKUP_DIR" not in e2e.generate_env(KEYS)
        values = e2e.generate_env(KEYS, backup_dir="/srv/x/backups")
        assert values["BACKUP_DIR"] == "/srv/x/backups"

    def test_sign_in_sends_credentials_on_stdin_and_returns_the_token(
        self, monkeypatch, tmp_path
    ):
        seen = {}

        def fake_run(env_file, *args, stdin=None):
            seen["args"], seen["stdin"] = args, stdin
            return FakeProcess(0, json.dumps({"access_token": FAKE_JWT}))

        monkeypatch.setattr(e2e, "run_compose", fake_run)
        assert e2e.sign_in(tmp_path / ".env", 1, "pw-123") == FAKE_JWT
        assert json.loads(seen["stdin"]) == {
            "email": "selfhost-test-1@example.com",
            "password": "pw-123",
        }
        assert "pw-123" not in " ".join(seen["args"])

    def test_sign_in_failure_is_reported(self, monkeypatch, tmp_path):
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: FakeProcess(1, ""))
        with pytest.raises(e2e.E2EFailure, match="sign-in 1 failed"):
            e2e.sign_in(tmp_path / ".env", 1, "pw")

    def test_sign_up_can_use_a_password_given_to_it(self, monkeypatch, tmp_path):
        seen = {}

        def fake_run(env_file, *args, stdin=None):
            seen["stdin"] = stdin
            return FakeProcess(0, json.dumps({"access_token": FAKE_JWT}))

        monkeypatch.setattr(e2e, "run_compose", fake_run)
        e2e.sign_up(tmp_path / ".env", 1, "chosen-password")
        assert json.loads(seen["stdin"])["password"] == "chosen-password"  # noqa: S105

    def test_lineup_sh_is_pointed_at_the_test_stack(self, tmp_path):
        env = e2e.lineup_sh_environment(tmp_path / ".env")
        assert env["LINEUP_ENV_FILE"] == str(tmp_path / ".env")
        assert env["LINEUP_PROJECT"] == "lineup-selfhost-test"
        assert env["LINEUP_LANG"] == "en"
        files = env["LINEUP_COMPOSE_FILES"].split()
        assert [Path(f).relative_to(e2e.ROOT).as_posix() for f in files] == [
            "selfhost/compose.yml",
            "selfhost/compose.test.yml",
        ]

    def test_run_lineup_sh_gives_it_no_input_and_returns_its_exit_code(
        self, monkeypatch, tmp_path
    ):
        seen = {}

        def fake_run(command, **kwargs):
            seen["command"], seen["kwargs"] = command, kwargs
            return subprocess.CompletedProcess(command, 7)

        monkeypatch.setattr(e2e.subprocess, "run", fake_run)
        assert e2e.run_lineup_sh(tmp_path / ".env", "restore", "--yes-restore") == 7
        assert seen["command"][1:] == [
            str(e2e.LINEUP_SH),
            "restore",
            "--yes-restore",
        ]
        assert seen["kwargs"]["stdin"] == subprocess.DEVNULL

    def test_team_names_reads_the_first_page(self, monkeypatch):
        body = json.dumps({"items": [{"name": "A"}, {"name": "B"}]}).encode()
        monkeypatch.setattr(e2e, "http", lambda *a, **k: (200, {}, body))
        assert e2e.team_names(FAKE_JWT) == ["A", "B"]

    def test_team_names_fails_on_a_bad_status(self, monkeypatch):
        monkeypatch.setattr(e2e, "http", lambda *a, **k: (401, {}, b""))
        with pytest.raises(e2e.E2EFailure, match="401"):
            e2e.team_names(FAKE_JWT)

    def test_count_rows_asks_the_database_as_its_owner(self, monkeypatch, tmp_path):
        seen = {}

        def fake_run(env_file, *args, stdin=None):
            seen["args"] = args
            return FakeProcess(0, "3\n")

        monkeypatch.setattr(e2e, "run_compose", fake_run)
        assert e2e.count_rows(tmp_path / ".env", "refresh_tokens") == 3
        assert seen["args"][:6] == ("exec", "-T", "db", "psql", "-U", "postgres")
        assert "auth.refresh_tokens" in seen["args"][-1]

    def test_count_rows_failure(self, monkeypatch, tmp_path):
        monkeypatch.setattr(e2e, "run_compose", lambda *a, **k: FakeProcess(1, ""))
        with pytest.raises(e2e.E2EFailure, match="could not count"):
            e2e.count_rows(tmp_path / ".env", "sessions")

    @pytest.fixture
    def world(self, monkeypatch):
        """A pretend stack: teams that can be deleted and restored, and a record of the steps.

        `fail` maps a step ("create", "delete", "backup", "restore", "gone", "listed", "back") to
        the way it should misbehave.
        """
        state = {
            "teams": [],
            "backed_up": [],
            "events": [],
            "tokens": [2],
            "fail": {},
        }

        def http(method, path, token=None, body=None):
            if method == "POST":
                state["events"].append("create")
                if "create" in state["fail"]:
                    return 500, {}, b""
                state["teams"].append(body["name"])
                return 201, {}, json.dumps({"id": "team-1"}).encode()
            state["events"].append("delete")
            if "delete" in state["fail"]:
                return 500, {}, b""
            if "gone" not in state["fail"]:
                state["teams"].clear()
            return 204, {}, b""

        def lineup_sh(env_file, *args):
            state["events"].append(args[0])
            if args[0] == "backup":
                state["backed_up"] = list(state["teams"])
                return 1 if "backup" in state["fail"] else 0
            if args[2] == "1999-01-01":
                return 0 if "no-failure" in state["fail"] else 1
            state["teams"][:] = [] if "back" in state["fail"] else state["backed_up"]
            state["tokens"] = [5 if "tokens" in state["fail"] else 0]
            return 1 if "restore" in state["fail"] else 0

        def team_names(token):
            if token == "fresh.token.value" and "back" in state["fail"]:  # noqa: S105
                return []
            if "listed" in state["fail"] and "create" in state["events"][-1:]:
                return []
            return list(state["teams"])

        monkeypatch.setattr(e2e, "http", http)
        monkeypatch.setattr(e2e, "team_names", team_names)
        monkeypatch.setattr(e2e, "run_lineup_sh", lineup_sh)
        monkeypatch.setattr(
            e2e, "count_rows", lambda env_file, table: state["tokens"][0]
        )
        monkeypatch.setattr(e2e, "sign_in", lambda *a: "fresh.token.value")
        return state

    def check(self, tmp_path):
        e2e.check_backup_and_restore(tmp_path / ".env", FAKE_JWT, "pw")

    def test_the_whole_sequence(self, world, tmp_path):
        self.check(tmp_path)
        assert world["events"] == ["create", "backup", "delete", "restore", "restore"]

    @pytest.mark.parametrize(
        ("fail", "message"),
        [
            ("create", "creating the team answered 500"),
            ("listed", "not listed"),
            ("backup", "lineup.sh backup failed"),
            ("delete", "deleting the team answered 500"),
            ("gone", "still listed"),
            ("restore", "lineup.sh restore failed"),
            ("tokens", "backups must leave them out"),
            ("no-failure", "did not fail"),
            ("back", "did not come back"),
        ],
    )
    def test_each_failure_is_named(self, world, tmp_path, fail, message):
        world["fail"][fail] = True
        with pytest.raises(e2e.E2EFailure, match=message):
            self.check(tmp_path)

    def test_there_must_be_sign_in_rows_to_leave_out(self, world, tmp_path):
        world["tokens"] = [0]
        with pytest.raises(e2e.E2EFailure, match="no sign-in rows"):
            self.check(tmp_path)

    def test_the_backup_folder_is_handed_back_before_the_stack_is_removed(
        self, monkeypatch, tmp_path
    ):
        seen = []

        def fake_run(env_file, *args, stdin=None):
            seen.append(args)
            return FakeProcess(0, "")

        monkeypatch.setattr(e2e, "run_compose", fake_run)
        e2e.release_backup_folder(tmp_path / ".env")
        args = seen[0]
        assert args[:2] == ("run", "--rm")
        assert "backup" in args and "chown" in args
        assert args[-2] == f"{e2e.os.getuid()}:{e2e.os.getgid()}"
        assert args[-1] == "/backups"
