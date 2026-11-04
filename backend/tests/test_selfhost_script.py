"""The operator tool of the self-hosted install: selfhost/lineup.sh and selfhost/backup/backup.sh.

The scripts run for real (bash through `subprocess`) in a throw-away install folder under `tmp_path`.
Everything outside them is replaced by small fake programs placed first on `PATH`, the same idea as the
fake `libreoffice` in test_pdf_converter.py: a fake `docker` that logs every call and answers from
settings the test writes, a fake `curl` that serves a pretend GitHub, and fake `df`/`uname`. No Docker,
network or database is used; `task selfhost:test` runs the same commands against the real stack.

What the tests prove: nothing secret is ever printed, `.env` is private and is never overwritten, a file
given to `--from-file` is parsed and never executed, an update that cannot be backed up or verified does
not touch anything, a failed update is undone only when the database was not changed, a restore needs the
typed word, and the two message files define exactly the same messages.
"""

import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import tarfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELFHOST = ROOT / "selfhost"
README = ROOT / "README.md"

TUNNEL_TOKEN = "tunnel-token-SECRET123"
GOOGLE_SECRET = "GOCSPX-google-SECRET-456"
KEY_MATERIAL = "FAKE-PRIVATE-KEY-MATERIAL"
# The fake docker hands out 1001, 1002, ... as 48-digit secrets (the real ones are 48 hex digits).
GENERATED = [f"{n:048d}" for n in range(1001, 1005)]
SECRETS = [TUNNEL_TOKEN, GOOGLE_SECRET, KEY_MATERIAL, *GENERATED]

FAKE_DOCKER = r"""#!/bin/bash
# Fake docker: logs the call, answers from the files in $FAKE_STATE. "next" pops the first line of a
# sequence file (one value per call) and falls back to a default.
printf '%s\n' "$*" >> "$FAKE_STATE/docker.log"
next() {
  local file="$FAKE_STATE/$1" value
  if [ -s "$file" ]; then
    value="$(head -n 1 "$file")"
    tail -n +2 "$file" > "$file.tmp"
    mv "$file.tmp" "$file"
    printf '%s' "$value"
  else
    printf '%s' "$2"
  fi
}
args="$*"
case "$1" in
  info)
    case "$(next info ok)" in
      ok) exit 0 ;;
      denied) echo "permission denied while trying to connect to the Docker daemon socket" >&2; exit 1 ;;
      *) echo "Cannot connect to the Docker daemon. Is the docker daemon running?" >&2; exit 1 ;;
    esac ;;
  run)
    if [[ "$args" == *secrets.token_hex* ]]; then
      n="$(cat "$FAKE_STATE/secret_n" 2>/dev/null || echo 1000)"
      n=$((n + 1)); echo "$n" > "$FAKE_STATE/secret_n"
      printf '%048d\n' "$n"
    elif [[ "$args" == *lineup.auth.signing_key* ]]; then
      echo '[{"kty":"EC","d":"FAKE-PRIVATE-KEY-MATERIAL"}]'
    fi
    exit "$(next run_exit 0)" ;;
  compose)
    if [[ "$args" == *"version --short"* ]]; then
      echo "$(next compose_version 2.30.1)"; exit 0
    elif [[ "$args" == *" run "*"backup --once"* ]]; then
      echo "backup: ok"; exit "$(next backup 0)"
    elif [[ "$args" == *" run "*"--entrypoint alembic"* ]]; then
      [ -f "$FAKE_STATE/revision_fail" ] && exit 1
      echo "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl." >&2
      echo "$(next revision abc123) (head)"; exit 0
    elif [[ "$args" == *" run "*"--entrypoint ls backup"* ]]; then
      [ -f "$FAKE_STATE/ls" ] && cat "$FAKE_STATE/ls"; exit 0
    elif [[ "$args" == *" run "*"--entrypoint cat backup"* ]]; then
      [ -f "$FAKE_STATE/last_success" ] && cat "$FAKE_STATE/last_success" && exit 0; exit 1
    elif [[ "$args" == *" run "*"--entrypoint pg_restore"* ]]; then
      exit "$(next restore 0)"
    elif [[ "$args" == *" run "*"--entrypoint sh backup -c cd /backups"* ]]; then
      echo "12K	lineup-2026-11-04.dump"; echo "40K	auth-2026-11-04.dump"; exit 0
    elif [[ "$args" == *" exec "* ]]; then
      exit "$(next health 0)"
    elif [[ "$args" == *" up "* ]]; then
      exit "$(next up 0)"
    elif [[ "$args" == *" pull"* ]]; then
      exit "$(next pull 0)"
    elif [[ "$args" == *" ps "* ]]; then
      echo "SERVICE STATE STATUS"; echo "api running Up 2 hours (healthy)"; exit 0
    fi
    exit 0 ;;
esac
exit 0
"""

FAKE_CURL = r"""#!/bin/bash
# Fake curl: a pretend GitHub in $FAKE_WEB. The last argument is the URL; -o names an output file.
args=("$@")
url="${args[${#args[@]}-1]}"
out=""
for ((i = 0; i < ${#args[@]}; i++)); do
  [ "${args[i]}" = "-o" ] && out="${args[i+1]}"
done
printf '%s\n' "$url" >> "$FAKE_STATE/curl.log"
case "$url" in
  https://ghcr.io/*) exit "${FAKE_GHCR_EXIT:-0}" ;;
  *"/releases?per_page=1")
    [ -f "$FAKE_WEB/releases.json" ] || exit 22
    cat "$FAKE_WEB/releases.json" ;;
  */releases/download/*/*)
    name="${url##*/}"
    [ -f "$FAKE_WEB/$name" ] || exit 22
    if [ -n "$out" ]; then cp "$FAKE_WEB/$name" "$out"; else cat "$FAKE_WEB/$name"; fi ;;
  *) exit 22 ;;
esac
"""

FAKE_DF = """#!/bin/bash
echo "Filesystem 1024-blocks Used Available Capacity Mounted on"
echo "/dev/fake 99999999 1 ${FAKE_DF_KB:-52428800} 1% /"
"""

FAKE_UNAME = """#!/bin/bash
echo "${FAKE_ARCH:-x86_64}"
"""

FAKE_PG_DUMP = r"""#!/bin/bash
# Fake pg_dump: records its arguments, writes the --file, fails for the database in $FAKE_FAIL_DB.
printf '%s\n' "$*" >> "$BACKUPS_DIR/pg_dump.calls"
db=""; file=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dbname) db="$2"; shift 2 ;;
    --file) file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [ "$db" = "${FAKE_FAIL_DB:-}" ]; then
  echo "ERROR: SELECT secret FROM users failed (SQL DETAIL)" >&2
  exit 3
fi
echo "dump of $db" > "$file"
"""

HU_NAMES = ("VISSZAALLIT", "IGEN")


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


class Box:
    """A throw-away install folder with the fake programs, and a way to run lineup.sh in it."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "lineup"
        self.bin = tmp_path / "bin"
        self.state = tmp_path / "state"
        self.web = tmp_path / "web"
        self.tmp = tmp_path
        for folder in (self.root, self.bin, self.state, self.web):
            folder.mkdir()
        shutil.copy(SELFHOST / "lineup.sh", self.root / "lineup.sh")
        shutil.copytree(SELFHOST / "messages", self.root / "messages")
        shutil.copytree(SELFHOST / "backup", self.root / "backup")
        (self.root / "compose.yml").write_text("# compose old\n")
        (self.root / "VERSION").write_text("v0.1.0\n")
        (self.root / "postgres-init").mkdir()
        (self.root / "postgres-init" / "01-databases.sh").write_text("# init old\n")
        for name, text in (
            ("docker", FAKE_DOCKER),
            ("curl", FAKE_CURL),
            ("df", FAKE_DF),
            ("uname", FAKE_UNAME),
        ):
            _write_executable(self.bin / name, text)
        (tmp_path / "meminfo").write_text("MemTotal:        8000000 kB\n")
        self.old_script = (self.root / "lineup.sh").read_bytes()

    @property
    def env_file(self) -> Path:
        """The install's .env."""
        return self.root / ".env"

    def environment(self, lang: str | None = "en", **extra: str) -> dict[str, str]:
        """The environment of a run: the fake programs first on PATH and the test-only settings."""
        env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.tmp),
            "TERM": "dumb",
            "FAKE_STATE": str(self.state),
            "FAKE_WEB": str(self.web),
            "LINEUP_MEMINFO_FILE": str(self.tmp / "meminfo"),
            "LINEUP_HEALTH_TRIES": "1",
            "LINEUP_HEALTH_SLEEP": "0",
        }
        if lang:
            env["LINEUP_LANG"] = lang
        env.update(extra)
        return env

    def run(
        self, *args: str, input: str = "", lang: str | None = "en", **extra: str
    ) -> subprocess.CompletedProcess:
        """Run `bash lineup.sh <args>` and capture text output. Never raises on a non-zero exit."""
        return subprocess.run(  # noqa: S603
            ["bash", str(self.root / "lineup.sh"), *args],  # noqa: S607
            input=input,
            capture_output=True,
            text=True,
            env=self.environment(lang, **extra),
            cwd=self.tmp,
            timeout=60,
            check=False,
        )

    def path_without(self, *missing: str) -> str:
        """A PATH holding the fakes and only the basic tools the script needs, minus `missing`.

        Used to show what the script does on a machine that lacks docker, curl or wget (the real
        ones live in /usr/bin, so a PATH with that directory could not hide them).
        """
        tools = self.tmp / "tools"
        shutil.rmtree(tools, ignore_errors=True)
        tools.mkdir()
        basics = (
            "bash grep sed awk tr cat mktemp stat head tail sort fold date dirname mv cp rm mkdir "
            "chmod tar sleep printf env ls touch sha256sum"
        ).split()
        for name in basics:
            found = shutil.which(name)
            if found and name not in missing:
                (tools / name).symlink_to(found)
        for fake in self.bin.iterdir():
            if fake.name not in missing:
                (tools / fake.name).symlink_to(fake)
        return str(tools)

    def seq(self, name: str, *values: object) -> None:
        """Make the fake answer `name` with these values, one per call (then its default)."""
        (self.state / name).write_text("".join(f"{v}\n" for v in values))

    def flag(self, name: str, content: str = "1\n") -> None:
        """Create the state file `name` (a fake's switch or canned output)."""
        (self.state / name).write_text(content)

    def docker_calls(self) -> list[str]:
        """Every call the fake docker saw, one string per call."""
        log = self.state / "docker.log"
        return log.read_text().splitlines() if log.exists() else []

    def called(self, text: str) -> bool:
        """True when some docker call contains `text`."""
        return any(text in call for call in self.docker_calls())

    def index_of(self, text: str) -> int:
        """The position of the first docker call containing `text`."""
        return next(i for i, call in enumerate(self.docker_calls()) if text in call)

    def write_env(self, **overrides: str) -> None:
        """An installed .env (mode 600) with fake secrets whose values all contain SECRET."""
        values = {
            "LINEUP_VERSION": "v0.1.0",
            "LINEUP_LANG": "en",
            "PUBLIC_URL": "https://lineup.example.com",
            "COMPOSE_PROFILES": "tunnel",
            "TUNNEL_TOKEN": TUNNEL_TOKEN,
            "POSTGRES_PASSWORD": "pg-SECRET-1",
            "AUTH_DB_PASSWORD": "auth-SECRET-2",
            "LINEUP_APP_PASSWORD": "app-SECRET-3",
            "AUTH_JWT_SECRET": "jwt-SECRET-4",
            "AUTH_JWT_KEYS": f"'[{{\"d\":\"{KEY_MATERIAL}\"}}]'",
            "GOOGLE_CLIENT_ID": "client-id.apps.googleusercontent.com",
            "GOOGLE_SECRET": GOOGLE_SECRET,
            "BACKUP_DIR": str(self.tmp / "backups"),
            "AUTH_EMAIL_ENABLED": "false",
        }
        values.update(overrides)
        self.env_file.write_text("".join(f"{k}={v}\n" for k, v in values.items()))
        self.env_file.chmod(0o600)

    def env_value(self, name: str) -> str:
        """The value of `name` in .env (no quote handling needed for the values tests read)."""
        for line in self.env_file.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1]
        raise KeyError(name)

    def install_file(self, text: str | None = None, mode: int = 0o600) -> Path:
        """A --from-file input file with valid values (or `text`), with the given mode."""
        path = self.tmp / "install.txt"
        path.write_text(
            text
            if text is not None
            else (
                "# the five values\n"
                "PUBLIC_URL=https://lineup.example.com\n"
                f"TUNNEL_TOKEN={TUNNEL_TOKEN}\n"
                "GOOGLE_CLIENT_ID=client-id.apps.googleusercontent.com\n"
                f"GOOGLE_SECRET='{GOOGLE_SECRET}'\n"
                f"BACKUP_DIR={self.tmp}/backups\n"
            )
        )
        path.chmod(mode)
        return path

    def make_bundle(self, tag: str, *, evil: bool = False, bad_checksum: bool = False) -> None:
        """Publish `selfhost-<tag>.tar.gz` and its .sha256 on the pretend GitHub."""
        shutil.rmtree(self.tmp / f"bundle-{tag}", ignore_errors=True)
        source = self.tmp / f"bundle-{tag}" / "selfhost"
        (source / "backup").mkdir(parents=True)
        (source / "postgres-init").mkdir()
        (source / "messages").mkdir()
        (source / "compose.yml").write_text(f"# compose {tag}\n")
        (source / "lineup.sh").write_text(f"#!/usr/bin/env bash\n# script {tag}\n")
        (source / "lineup.sh").chmod(0o755)
        (source / "VERSION").write_text(f"{tag}\n")
        (source / "backup" / "backup.sh").write_text(f"#!/bin/bash\n# backup {tag}\n")
        (source / "backup" / "backup.sh").chmod(0o755)
        (source / "postgres-init" / "01-databases.sh").write_text(f"# init {tag}\n")
        for name in ("en.sh", "hu.sh"):
            shutil.copy(SELFHOST / "messages" / name, source / "messages" / name)
        # A bundle must never carry these, and the update must never install them.
        (source / ".env").write_text("LINEUP_VERSION=evil\n")
        name = f"selfhost-{tag}.tar.gz"
        archive = self.web / name
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(source, arcname="selfhost")
            if evil:
                payload = self.tmp / "payload.txt"
                payload.write_text("x")
                tar.add(payload, arcname="selfhost/../evil.txt")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if bad_checksum:
            digest = "0" * 64
        (self.web / f"{name}.sha256").write_text(f"{digest}  {name}\n")

    def publish_release(self, tag: str) -> None:
        """Make the pretend GitHub list `tag` as the newest release."""
        (self.web / "releases.json").write_text(
            '[\n  {\n    "url": "x",\n    "tag_name": "%s",\n    "prerelease": true\n  }\n]\n' % tag
        )

    def seed_backups(self, *ids: str) -> None:
        """Make the fake backup folder listing hold complete backups with these ids."""
        lines = []
        for backup_id in ids:
            lines += [f"auth-{backup_id}.dump", f"lineup-{backup_id}.dump"]
        self.flag("ls", "".join(f"{line}\n" for line in lines) + "last-success\n")


@pytest.fixture
def box(tmp_path):
    """A fresh install folder with fake programs."""
    return Box(tmp_path)


def keys_of(path: Path) -> set[str]:
    """The MSG_* names a messages file defines."""
    return set(re.findall(r"^(MSG_[A-Z0-9_]+)=", path.read_text(), re.MULTILINE))


def assert_no_secret(result: subprocess.CompletedProcess) -> None:
    """Fail when anything the fakes treat as a secret was printed."""
    output = result.stdout + result.stderr
    for secret in SECRETS:
        assert secret not in output
    assert "SECRET" not in output


# --- the files themselves ----------------------------------------------------------------------


class TestFiles:
    def test_the_scripts_are_executable_with_strict_bash(self):
        for path in (
            SELFHOST / "lineup.sh",
            SELFHOST / "backup" / "backup.sh",
        ):
            assert stat.S_IMODE(path.stat().st_mode) == 0o755
            text = path.read_text()
            assert "set -euo pipefail" in text
            assert not re.search(r"^\s*set\s+-\w*x", text, re.MULTILINE)
            assert not re.search(r"\bset\s+-o\s+xtrace", text)
        assert (SELFHOST / "lineup.sh").read_text().startswith("#!/usr/bin/env bash\n")
        assert (SELFHOST / "backup" / "backup.sh").read_text().startswith("#!/bin/bash\n")

    def test_the_script_does_not_depend_on_tools_the_host_may_lack(self):
        code = "\n".join(
            line
            for line in (SELFHOST / "lineup.sh").read_text().splitlines()
            if not line.lstrip().startswith("#")
        )
        for tool in ("jq", "python3", "openssl", "task"):
            assert not re.search(rf"(^|[\s|;(`$]){tool}\s", code), tool

    def test_both_languages_define_exactly_the_same_messages(self):
        english, hungarian = keys_of(SELFHOST / "messages" / "en.sh"), keys_of(
            SELFHOST / "messages" / "hu.sh"
        )
        assert english == hungarian
        assert len(english) > 100

    def test_every_message_the_script_uses_exists(self):
        script = (SELFHOST / "lineup.sh").read_text()
        used = set(re.findall(r"\b(?:m|say|say_err|prompt) ([A-Z][A-Z0-9_]+)", script))
        used |= set(re.findall(r"\$\(m ([A-Z][A-Z0-9_]+)", script))
        used |= set(re.findall(r"ask_valid IN_\w+ ([A-Z][A-Z0-9_]+)", script))
        defined = {key.removeprefix("MSG_") for key in keys_of(SELFHOST / "messages" / "en.sh")}
        assert used <= defined
        assert defined <= used, f"unused messages: {sorted(defined - used)}"

    def test_messages_are_valid_printf_formats_with_matching_placeholders(self):
        """A message in one language fills as many places as the other: a mismatch shifts arguments."""
        def formats(path: Path) -> dict[str, int]:
            result = {}
            for key, value in re.findall(
                r'^(MSG_[A-Z0-9_]+)="(.*)"$', path.read_text(), re.MULTILINE
            ):
                result[key] = len(re.findall(r"%s", value))
                assert not re.search(r"%[^s%]", value), f"{key} has a bad conversion"
            return result

        assert formats(SELFHOST / "messages" / "en.sh") == formats(SELFHOST / "messages" / "hu.sh")

    @pytest.mark.parametrize("lang", ["en", "hu"])
    def test_the_backup_limits_text_is_the_one_in_the_plan(self, lang):
        text = (SELFHOST / "messages" / f"{lang}.sh").read_text()
        match = re.search(r'^MSG_BACKUP_LIMITS="(.*)"$', text, re.MULTILINE)
        assert match
        limits = match.group(1)
        assert "30" in limits and ".env" in limits
        if lang == "en":
            assert limits == (
                "Backups run every night and are kept for 30 days, in a folder on this same machine. "
                "They are not encrypted, and anyone with access to this machine can read them. "
                "They protect against mistakes and bad updates. If this machine is lost or fails, "
                "all data is lost, unless someone has copied the backup folder elsewhere by hand. "
                "Also save the .env file somewhere safe and private: without it a restore on a new "
                "machine means everyone's sign-in and database passwords must be set up again."
            )

    def test_the_readme_states_the_same_limits(self):
        readme = " ".join(README.read_text().replace("**", "").replace("`", "").split())
        english = re.search(
            r'^MSG_BACKUP_LIMITS="(.*)"$',
            (SELFHOST / "messages" / "en.sh").read_text(),
            re.MULTILINE,
        ).group(1)
        assert english in readme


# --- doctor ------------------------------------------------------------------------------------


class TestDoctor:
    def test_a_ready_machine_passes(self, box):
        result = box.run("doctor")
        assert result.returncode == 0
        assert "Everything is fine" in result.stdout
        assert "[ PROBLEM ]" not in result.stdout

    def test_hungarian_is_the_default_language(self, box):
        result = box.run("doctor", lang=None)
        assert "RENDBEN" in result.stdout
        assert "Minden rendben van" in result.stdout

    def test_the_language_comes_from_env_when_not_overridden(self, box):
        box.write_env(LINEUP_LANG="en")
        assert "Everything is fine" in box.run("doctor", lang=None).stdout
        box.write_env(LINEUP_LANG="hu")
        assert "Minden rendben van" in box.run("doctor", lang=None).stdout

    def test_an_unknown_language_falls_back_to_hungarian(self, box):
        assert "RENDBEN" in box.run("doctor", lang="xx").stdout

    @pytest.mark.parametrize(
        ("kb", "code", "word"),
        [("8000000", 0, "Memory: 7.6 GB"), ("1500000", 0, "WARNING"), ("900000", 1, "PROBLEM")],
    )
    def test_memory_thresholds(self, box, kb, code, word):
        (box.tmp / "meminfo").write_text(f"MemTotal: {kb} kB\n")
        result = box.run("doctor")
        assert result.returncode == code
        assert word in result.stdout

    def test_unreadable_memory_is_a_warning_not_a_failure(self, box):
        (box.tmp / "meminfo").write_text("nothing useful\n")
        result = box.run("doctor")
        assert result.returncode == 0
        assert "Could not read how much memory" in result.stdout

    def test_low_disk_is_a_warning(self, box):
        result = box.run("doctor", FAKE_DF_KB="5000000")
        assert result.returncode == 0
        assert "only 4 GB" in result.stdout

    def test_every_problem_comes_with_what_to_do(self, box):
        (box.tmp / "meminfo").write_text("MemTotal: 900000 kB\n")
        result = box.run("doctor")
        assert result.stdout.count("[ PROBLEM ]") == result.stdout.count("What to do:")

    def test_an_unsupported_processor_is_a_problem(self, box):
        result = box.run("doctor", FAKE_ARCH="armv7l")
        assert result.returncode == 1
        assert "armv7l" in result.stdout

    @pytest.mark.parametrize(
        ("setting", "text"),
        [
            ("denied", "not allowed to use Docker"),
            ("down", "not running"),
        ],
    )
    def test_docker_that_cannot_be_used(self, box, setting, text):
        box.seq("info", setting)
        result = box.run("doctor")
        assert result.returncode == 1
        assert text in result.stdout

    def test_docker_missing_entirely(self, box):
        result = box.run("doctor", PATH=box.path_without("docker"))
        assert result.returncode == 1
        assert "Docker is not installed" in result.stdout

    @pytest.mark.parametrize("version", ["2.19.9", "1.29.2"])
    def test_an_old_compose_is_a_problem(self, box, version):
        box.seq("compose_version", version)
        result = box.run("doctor")
        assert result.returncode == 1
        assert "too old" in result.stdout

    @pytest.mark.parametrize("version", ["2.20.0", "v2.29.1", "5.6.1"])
    def test_a_new_enough_compose_passes(self, box, version):
        box.seq("compose_version", version)
        assert box.run("doctor").returncode == 0

    def test_a_missing_registry_is_a_problem(self, box):
        result = box.run("doctor", FAKE_GHCR_EXIT="6")
        assert result.returncode == 1
        assert "ghcr.io cannot be reached" in result.stdout

    def test_neither_curl_nor_wget_is_a_warning(self, box):
        result = box.run("doctor", PATH=box.path_without("curl", "wget"))
        assert result.returncode == 0
        assert "Neither curl nor wget" in result.stdout

    def test_wget_is_used_when_curl_is_missing(self, box):
        (box.bin / "curl").unlink()
        _write_executable(box.bin / "wget", "#!/bin/bash\nexit 8\n")
        result = box.run("doctor")
        assert result.returncode == 0
        assert "The internet can be reached" in result.stdout

    def test_unknown_options_are_refused(self, box):
        result = box.run("doctor", "--now")
        assert result.returncode == 2
        assert "--now" in result.stderr


# --- install -----------------------------------------------------------------------------------


class TestInstall:
    def test_it_refuses_to_overwrite_an_existing_env_file(self, box):
        box.write_env()
        before = box.env_file.read_text()
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert "already installed" in result.stderr
        assert box.env_file.read_text() == before
        assert box.docker_calls() == []
        assert_no_secret(result)

    def test_a_successful_install_writes_a_private_env_and_prints_no_secret(self, box):
        result = box.run(
            "install", "--from-file", str(box.install_file()), "--accept-backup-limits"
        )
        assert result.returncode == 0, result.stderr
        assert_no_secret(result)
        assert stat.S_IMODE(box.env_file.stat().st_mode) == 0o600
        assert not [p for p in box.root.iterdir() if p.name.startswith(".env.")]
        text = box.env_file.read_text()
        for line in (
            "LINEUP_VERSION=v0.1.0",
            "LINEUP_LANG=en",
            "PUBLIC_URL=https://lineup.example.com",
            "COMPOSE_PROFILES=tunnel",
            f"TUNNEL_TOKEN={TUNNEL_TOKEN}",
            f"GOOGLE_SECRET={GOOGLE_SECRET}",
            f"POSTGRES_PASSWORD={GENERATED[0]}",
            f"AUTH_DB_PASSWORD={GENERATED[1]}",
            f"LINEUP_APP_PASSWORD={GENERATED[2]}",
            f"AUTH_JWT_SECRET={GENERATED[3]}",
            "AUTH_JWT_KEYS='[{\"kty\":\"EC\",\"d\":\"FAKE-PRIVATE-KEY-MATERIAL\"}]'",
            f"BACKUP_DIR={box.tmp}/backups",
            "AUTH_EMAIL_ENABLED=false",
        ):
            assert line in text.splitlines()
        assert stat.S_IMODE((box.tmp / "backups").stat().st_mode) == 0o700
        assert str(box.env_file) in result.stdout
        assert "https://lineup.example.com" in result.stdout

    def test_it_generates_secrets_with_the_api_image_and_starts_the_stack(self, box):
        box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        image = "ghcr.io/lasterbergamot/lineup-api:v0.1.0"
        assert box.called(f"run --rm --entrypoint python {image} -c import secrets; print(secrets.token_hex(24))")
        assert box.called(f"run --rm --entrypoint python {image} -m lineup.auth.signing_key")
        chown = box.index_of("--user 0 --cap-add CHOWN --entrypoint sh backup -c chown 999:999 /backups")
        up = box.index_of("up -d --wait")
        health = box.index_of("exec -T api python -c")
        assert box.index_of("secrets.token_hex") < chown < up < health

    def test_the_hungarian_install_asks_for_the_hungarian_word(self, box):
        result = box.run(
            "install", "--from-file", str(box.install_file()), lang="hu", input="igen\n"
        )
        assert result.returncode == 0, result.stderr
        assert "IGEN" in result.stderr
        assert "30 napig" in result.stdout
        assert "LINEUP_LANG=hu" in box.env_file.read_text()

    def test_the_backup_limits_must_be_accepted_by_typing_the_word(self, box):
        result = box.run("install", "--from-file", str(box.install_file()), input="no thanks\n")
        assert result.returncode == 1
        assert "30 days" in result.stdout and "not encrypted" in result.stdout
        assert "YES" in result.stderr
        assert not box.env_file.exists()
        assert not box.called("up ")

    def test_the_typed_word_is_accepted_in_any_case(self, box):
        result = box.run("install", "--from-file", str(box.install_file()), input="yes\n")
        assert result.returncode == 0, result.stderr

    def test_the_language_in_the_file_wins_over_the_environment(self, box):
        path = box.install_file(box.install_file().read_text() + "LINEUP_LANG=hu\n")
        result = box.run("install", "--from-file", str(path), "--accept-backup-limits")
        assert result.returncode == 0
        assert "LINEUP_LANG=hu" in box.env_file.read_text()

    def test_interactive_install_asks_in_order_and_hides_nothing_in_the_output(self, box):
        answers = "\n".join(
            [
                "en",
                "https://lineup.example.com/",
                TUNNEL_TOKEN,
                "client-id.apps.googleusercontent.com",
                GOOGLE_SECRET,
                "",
                "YES",
                "",
            ]
        )
        result = box.run("install", input=answers, lang=None)
        assert result.returncode == 0, result.stderr
        assert_no_secret(result)
        assert box.env_value("PUBLIC_URL") == "https://lineup.example.com"
        assert box.env_value("BACKUP_DIR") == f"{box.root}/backups"
        assert box.env_value("LINEUP_LANG") == "en"

    def test_interactive_install_asks_again_after_an_invalid_value(self, box):
        answers = "\n".join(
            [
                "",
                "http://insecure.example.com",
                "https://lineup.example.com",
                TUNNEL_TOKEN,
                "client-id",
                GOOGLE_SECRET,
                f"{box.tmp}/elsewhere",
                "YES",
            ]
        )
        result = box.run("install", input=answers + "\n", lang="en")
        assert result.returncode == 0, result.stderr
        assert "not valid" in result.stderr
        assert box.env_value("BACKUP_DIR") == f"{box.tmp}/elsewhere"
        assert (box.tmp / "elsewhere").is_dir()

    def test_interactive_install_gives_up_after_three_bad_answers(self, box):
        result = box.run("install", input="en\nnope\nnope\nnope\n")
        assert result.returncode == 1
        assert "Too many invalid answers" in result.stderr
        assert not box.env_file.exists()

    def test_an_unrecognised_language_answer_means_hungarian(self, box):
        result = box.run("install", input="klingon\n", lang=None)
        assert result.returncode == 1
        assert "Öt adatra" in result.stdout

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://lineup.example.com",
            "https://lineup.example.com/app",
            "lineup.example.com",
            "https://lineup example.com",
        ],
    )
    def test_the_public_address_must_be_https_without_a_path(self, box, bad_url):
        path = box.install_file(
            f"PUBLIC_URL={bad_url}\nTUNNEL_TOKEN=t\nGOOGLE_CLIENT_ID=c\nGOOGLE_SECRET=s\n"
        )
        result = box.run("install", "--from-file", str(path), "--accept-backup-limits")
        assert result.returncode == 1
        assert not box.env_file.exists()
        assert "https://" in result.stderr

    @pytest.mark.parametrize(
        "line",
        ["TUNNEL_TOKEN=", "GOOGLE_SECRET=has space", "GOOGLE_CLIENT_ID=quo'te", "TUNNEL_TOKEN=a$b"],
    )
    def test_a_value_the_env_file_could_not_carry_is_refused(self, box, line):
        text = box.install_file().read_text() + line + "\n"
        result = box.run("install", "--from-file", str(box.install_file(text)), "--accept-backup-limits")
        assert result.returncode == 1
        assert not box.env_file.exists()
        assert_no_secret(result)

    def test_the_backup_folder_must_be_an_absolute_plain_path(self, box):
        text = box.install_file().read_text() + "BACKUP_DIR=relative/dir\n"
        result = box.run("install", "--from-file", str(box.install_file(text)), "--accept-backup-limits")
        assert result.returncode == 1
        assert "full path" in result.stderr

    def test_a_file_that_others_can_read_is_refused(self, box):
        result = box.run(
            "install", "--from-file", str(box.install_file(mode=0o644)), "--accept-backup-limits"
        )
        assert result.returncode == 1
        assert "chmod 600" in result.stderr
        assert not box.env_file.exists()
        assert box.docker_calls() == []
        assert_no_secret(result)

    def test_a_missing_file_is_reported(self, box):
        result = box.run("install", "--from-file", str(box.tmp / "none"), "--accept-backup-limits")
        assert result.returncode == 1
        assert "does not exist" in result.stderr

    def test_the_file_is_parsed_and_never_executed(self, box):
        marker = box.tmp / "executed"
        text = (
            f"PUBLIC_URL=https://lineup.example.com\n"
            f"TUNNEL_TOKEN=$(touch {marker})\n"
            f"GOOGLE_CLIENT_ID=`touch {marker}`\n"
            f"GOOGLE_SECRET=x; touch {marker}\n"
            f"touch {marker}\n"
            "UNKNOWN_NAME=whatever\n"
        )
        result = box.run("install", "--from-file", str(box.install_file(text)), "--accept-backup-limits")
        assert result.returncode == 1
        assert not marker.exists()
        assert not box.env_file.exists()
        assert "ignored" in result.stderr
        assert "whatever" not in result.stderr

    def test_a_file_with_quotes_and_windows_line_endings_is_read(self, box):
        text = (
            "PUBLIC_URL=\"https://lineup.example.com\"\r\n"
            f"TUNNEL_TOKEN='{TUNNEL_TOKEN}'\r\n"
            "GOOGLE_CLIENT_ID=client-id\r\n"
            f"GOOGLE_SECRET={GOOGLE_SECRET}\r\n"
        )
        result = box.run("install", "--from-file", str(box.install_file(text)), "--accept-backup-limits")
        assert result.returncode == 0, result.stderr
        assert box.env_value("PUBLIC_URL") == "https://lineup.example.com"
        assert box.env_value("TUNNEL_TOKEN") == TUNNEL_TOKEN

    def test_the_doctor_runs_first_and_a_problem_stops_the_install(self, box):
        box.seq("info", "down")
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert "not running" in result.stdout
        assert "Nothing was changed" in result.stderr
        assert not box.env_file.exists()
        assert not box.called("secrets.token_hex")

    def test_a_missing_version_file_stops_the_install(self, box):
        (box.root / "VERSION").unlink()
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert "VERSION" in result.stderr

    def test_a_failed_image_download_writes_nothing(self, box):
        box.seq("run_exit", 1)
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert not box.env_file.exists()
        assert_no_secret(result)

    def test_a_bad_generated_secret_writes_nothing(self, box):
        _write_executable(box.bin / "docker", "#!/bin/bash\n[[ \"$1\" == info ]] && exit 0\n"
                          "[[ \"$*\" == *version* ]] && { echo 2.30.1; exit 0; }\necho not-hex\n")
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert not box.env_file.exists()

    def test_a_failed_start_keeps_the_settings_and_says_what_to_do(self, box):
        box.seq("up", 1)
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert box.env_file.exists()
        assert "do not run install again" in result.stderr
        assert "docker compose up -d --wait" in result.stderr
        assert_no_secret(result)

    def test_a_stack_that_never_answers_keeps_the_settings(self, box):
        box.seq("health", 1)
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert "does not answer" in result.stderr
        assert box.env_file.exists()
        assert_no_secret(result)

    def test_a_folder_that_cannot_be_prepared_is_reported(self, box):
        box.seq("run_exit", 0, 0, 0, 0, 0)  # the five image runs
        # the next `docker compose run` (the chown) fails: a compose run is "compose ... run ... chown"
        _write_executable(
            box.bin / "docker",
            (box.bin / "docker").read_text().replace(
                'if [[ "$args" == *"version --short"* ]]; then',
                'if [[ "$args" == *"--cap-add CHOWN"* ]]; then exit 1\n    elif [[ "$args" == *"version --short"* ]]; then',
            ),
        )
        result = box.run("install", "--from-file", str(box.install_file()), "--accept-backup-limits")
        assert result.returncode == 1
        assert "backup folder" in result.stderr
        assert box.env_file.exists()
        assert_no_secret(result)

    def test_unknown_options_are_refused(self, box):
        assert box.run("install", "--bogus").returncode == 2
        assert box.run("install", "--from-file").returncode == 2


# --- backup ------------------------------------------------------------------------------------


class TestBackup:
    def test_it_needs_an_installed_lineup(self, box):
        result = box.run("backup")
        assert result.returncode == 1
        assert "not installed" in result.stderr

    def test_it_runs_one_backup_and_lists_the_files(self, box):
        box.write_env()
        result = box.run("backup")
        assert result.returncode == 0, result.stderr
        assert box.called("run --rm -T backup --once")
        assert "lineup-2026-11-04.dump" in result.stdout
        assert str(box.tmp / "backups") in result.stdout
        assert_no_secret(result)

    def test_it_prepares_the_folder_first_and_gives_it_to_the_backup_user(self, box):
        box.write_env()
        box.run("backup")
        assert stat.S_IMODE((box.tmp / "backups").stat().st_mode) == 0o700
        assert box.index_of("--cap-add CHOWN") < box.index_of("backup --once")
        assert not box.called("--cap-add FOWNER")

    def test_a_failing_backup_says_so(self, box):
        box.write_env()
        box.seq("backup", 1)
        result = box.run("backup")
        assert result.returncode == 1
        assert "The backup failed" in result.stderr
        assert "Older backups were not touched" in result.stderr

    def test_the_default_folder_is_inside_the_install(self, box):
        box.write_env(BACKUP_DIR="")
        assert box.run("backup").returncode == 0
        assert (box.root / "backups").is_dir()

    def test_unknown_options_are_refused(self, box):
        box.write_env()
        assert box.run("backup", "--now").returncode == 2


# --- restore -----------------------------------------------------------------------------------


class TestRestore:
    @pytest.fixture
    def installed(self, box):
        box.write_env()
        box.seed_backups("2026-11-01", "2026-11-02")
        return box

    def test_it_needs_an_installed_lineup(self, box):
        assert box.run("restore", "--date", "2026-11-01").returncode == 1

    def test_it_refuses_without_the_typed_word(self, installed):
        result = installed.run("restore", "--date", "2026-11-02", input="no\n")
        assert result.returncode == 1
        assert "RESTORE" in result.stderr
        assert "replaces ALL current data" in result.stdout
        assert "sign in again" in result.stdout
        assert not installed.called("pg_restore")
        assert not installed.called(" stop ")
        assert not installed.called("--safety")

    def test_it_refuses_with_no_input_at_all(self, installed):
        assert installed.run("restore", "--date", "2026-11-02").returncode == 1
        assert not installed.called("pg_restore")

    def test_the_typed_word_is_language_specific(self, installed):
        refused = installed.run("restore", "--date", "2026-11-02", input="RESTORE\n", lang="hu")
        assert refused.returncode == 1
        assert not installed.called("pg_restore")
        accepted = installed.run("restore", "--date", "2026-11-02", input="visszaallit\n", lang="hu")
        assert accepted.returncode == 0, accepted.stderr
        assert installed.called("pg_restore")

    def test_it_lists_the_dates_and_asks_when_none_is_given(self, installed):
        result = installed.run("restore", input="2026-11-01\nrestore\n")
        assert result.returncode == 0, result.stderr
        assert "    2026-11-01" in result.stdout and "    2026-11-02" in result.stdout
        assert "/backups/lineup-2026-11-01.dump" in "\n".join(installed.docker_calls())

    def test_an_incomplete_backup_is_not_offered(self, installed):
        installed.flag("ls", "lineup-2026-11-03.dump\nauth-2026-11-02.dump\nlineup-2026-11-02.dump\n")
        result = installed.run("restore", "--date", "2026-11-03", "--yes-restore")
        assert result.returncode == 1
        assert "    2026-11-02" in result.stderr
        assert "2026-11-03.dump" not in result.stderr
        assert not installed.called("pg_restore")

    def test_an_unknown_date_is_refused_and_the_choices_are_shown(self, installed):
        result = installed.run("restore", "--date", "1999-01-01", "--yes-restore")
        assert result.returncode == 1
        assert "no backup with that date" in result.stderr
        assert "2026-11-01" in result.stderr
        assert not installed.called("pg_restore")

    @pytest.mark.parametrize("date", ["2026-11-0", "*", "../etc", "2026-11-01; id", ""])
    def test_a_date_that_is_not_a_listed_backup_never_reaches_a_command(self, installed, date):
        result = installed.run("restore", "--date", date, "--yes-restore")
        assert result.returncode == 1
        assert not installed.called("pg_restore")

    def test_no_backups_at_all(self, box):
        box.write_env()
        result = box.run("restore", "--date", "2026-11-01", "--yes-restore")
        assert result.returncode == 1
        assert "no backup to restore from" in result.stderr

    def test_an_unreadable_backup_folder_is_reported(self, installed):
        _write_executable(
            installed.bin / "docker",
            (installed.bin / "docker").read_text().replace(
                'elif [[ "$args" == *" run "*"--entrypoint ls backup"* ]]; then',
                'elif [[ "$args" == *" run "*"--entrypoint ls backup"* ]]; then exit 1\n    elif false; then',
            ),
        )
        result = installed.run("restore", "--date", "2026-11-01", "--yes-restore")
        assert result.returncode == 1
        assert "Could not read the backup folder" in result.stderr

    def test_the_restore_order_and_the_pg_restore_flags(self, installed):
        result = installed.run("restore", "--date", "2026-11-02", "--yes-restore")
        assert result.returncode == 0, result.stderr
        assert "Restored the backup of 2026-11-02" in result.stdout
        assert "sign in again" in result.stdout
        safety = installed.index_of("backup --once --safety")
        stop = installed.index_of(" stop web api auth")
        lineup = installed.index_of("--dbname lineup /backups/lineup-2026-11-02.dump")
        auth = installed.index_of("--dbname auth /backups/auth-2026-11-02.dump")
        up = installed.index_of(" up -d --wait")
        assert safety < stop < lineup < auth < up
        for call in installed.docker_calls():
            if "pg_restore" in call:
                assert "--clean --if-exists" in call
                assert "--no-owner" not in call
        assert_no_secret(result)

    def test_a_failed_safety_copy_stops_everything(self, installed):
        installed.seq("backup", 1)
        result = installed.run("restore", "--date", "2026-11-02", "--yes-restore")
        assert result.returncode == 1
        assert "safety copy could not be made" in result.stderr
        assert not installed.called(" stop ")
        assert not installed.called("pg_restore")

    def test_a_failed_restore_leaves_the_website_stopped_and_says_what_to_do(self, installed):
        installed.seq("restore", 1)
        result = installed.run("restore", "--date", "2026-11-02", "--yes-restore")
        assert result.returncode == 1
        assert "Run the same restore command again" in result.stderr
        assert not installed.called(" up -d")
        assert_no_secret(result)

    def test_a_stack_that_does_not_answer_afterwards_is_reported(self, installed):
        installed.seq("health", 1)
        result = installed.run("restore", "--date", "2026-11-02", "--yes-restore")
        assert result.returncode == 1
        assert "does not answer" in result.stderr

    def test_unknown_options_are_refused(self, installed):
        assert installed.run("restore", "--everything").returncode == 2
        assert installed.run("restore", "--date").returncode == 2


# --- update ------------------------------------------------------------------------------------


class TestUpdate:
    @pytest.fixture
    def ready(self, box):
        """An installed v0.1.0 with a v0.2.0 release published."""
        box.write_env()
        box.make_bundle("v0.2.0")
        box.publish_release("v0.2.0")
        return box

    def snapshot(self, box) -> dict[str, bytes]:
        """The bytes of every managed file and of .env."""
        files = {}
        for name in ("lineup.sh", "compose.yml", "VERSION", ".env"):
            files[name] = (box.root / name).read_bytes()
        files["init"] = (box.root / "postgres-init" / "01-databases.sh").read_bytes()
        files["backup.sh"] = (box.root / "backup" / "backup.sh").read_bytes()
        return files

    def test_it_needs_an_installed_lineup(self, box):
        assert box.run("update").returncode == 1

    def test_a_successful_update(self, ready):
        before = self.snapshot(ready)
        env_before = ready.env_file.read_text()
        (ready.tmp / "backups").mkdir()
        (ready.tmp / "backups" / "keep.dump").write_text("keep")
        result = ready.run("update")
        assert result.returncode == 0, result.stderr
        assert "Updated to v0.2.0" in result.stdout
        assert (ready.root / "compose.yml").read_text() == "# compose v0.2.0\n"
        assert (ready.root / "VERSION").read_text().strip() == "v0.2.0"
        assert (ready.root / "postgres-init" / "01-databases.sh").read_text() == "# init v0.2.0\n"
        assert stat.S_IMODE((ready.root / "backup" / "backup.sh").stat().st_mode) == 0o755
        assert stat.S_IMODE((ready.root / "lineup.sh").stat().st_mode) == 0o755
        # the old files are kept in previous/, .env and the backups are untouched
        assert (ready.root / "previous" / "compose.yml").read_bytes() == before["compose.yml"]
        assert (ready.root / "previous" / "lineup.sh").read_bytes() == before["lineup.sh"]
        assert ready.env_file.read_text() == env_before.replace("v0.1.0", "v0.2.0")
        assert stat.S_IMODE(ready.env_file.stat().st_mode) == 0o600
        assert "evil" not in ready.env_file.read_text()
        assert (ready.tmp / "backups" / "keep.dump").read_text() == "keep"
        assert not [p for p in ready.root.iterdir() if p.name.startswith(".update")]
        assert not [p for p in ready.root.iterdir() if p.name.startswith(".env.")]
        order = [ready.index_of(t) for t in ("backup --once", "alembic migrate current", " pull", " up -d --wait")]
        assert order == sorted(order)
        assert_no_secret(result)

    def test_the_newest_release_is_read_from_the_releases_list_not_latest(self, ready):
        ready.run("update")
        urls = (ready.state / "curl.log").read_text().splitlines()
        assert urls[0] == "https://api.github.com/repos/LasterBergamot/lineup/releases?per_page=1"
        assert not any("/releases/latest" in url for url in urls)
        assert "https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz" in urls
        assert "https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz.sha256" in urls

    def test_an_explicit_version_skips_the_lookup(self, ready):
        ready.make_bundle("v0.3.0-rc1")
        result = ready.run("update", "--version", "v0.3.0-rc1")
        assert result.returncode == 0, result.stderr
        assert "releases?per_page=1" not in (ready.state / "curl.log").read_text()
        assert ready.env_value("LINEUP_VERSION") == "v0.3.0-rc1"

    def test_nothing_happens_when_already_current(self, ready):
        ready.publish_release("v0.1.0")
        result = ready.run("update")
        assert result.returncode == 0
        assert "Already on the newest version (v0.1.0)" in result.stdout
        assert ready.docker_calls() == []
        assert not (ready.root / "previous").exists()

    @pytest.mark.parametrize("version", ["0.2.0", "v0.2", "latest", "v1.0.0; rm -rf /", "../v1.0.0"])
    def test_a_version_that_is_not_a_tag_is_refused(self, ready, version):
        result = ready.run("update", "--version", version)
        assert result.returncode == 1
        assert ready.docker_calls() == []

    def test_a_missing_release_list_is_explained(self, ready):
        (ready.web / "releases.json").unlink()
        result = ready.run("update")
        assert result.returncode == 1
        assert "Could not find out the newest version" in result.stderr
        assert "--version" in result.stderr

    def test_a_release_list_without_a_usable_tag_is_explained(self, ready):
        (ready.web / "releases.json").write_text('[{"tag_name": "nightly"}]')
        assert ready.run("update").returncode == 1

    def test_a_failed_download_changes_nothing(self, ready):
        (ready.web / "selfhost-v0.2.0.tar.gz").unlink()
        before = self.snapshot(ready)
        result = ready.run("update")
        assert result.returncode == 1
        assert "Could not download version v0.2.0" in result.stderr
        assert self.snapshot(ready) == before
        assert ready.docker_calls() == []

    def test_a_checksum_mismatch_stops_before_anything_is_touched(self, ready):
        ready.make_bundle("v0.2.0", bad_checksum=True)
        before = self.snapshot(ready)
        result = ready.run("update")
        assert result.returncode == 1
        assert "does not match its checksum" in result.stderr
        assert "NOT used" in result.stderr
        assert self.snapshot(ready) == before
        assert not (ready.root / "previous").exists()
        assert ready.docker_calls() == []

    def test_a_bundle_that_escapes_its_folder_is_refused(self, ready):
        ready.make_bundle("v0.2.0", evil=True)
        before = self.snapshot(ready)
        result = ready.run("update")
        assert result.returncode == 1
        assert "not a valid Lineup package" in result.stderr
        assert self.snapshot(ready) == before
        assert not (ready.tmp / "evil.txt").exists()

    def test_a_bundle_that_is_for_another_version_is_refused(self, ready):
        ready.make_bundle("v0.2.0")
        archive = ready.web / "selfhost-v0.9.9.tar.gz"
        shutil.copy(ready.web / "selfhost-v0.2.0.tar.gz", archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (ready.web / "selfhost-v0.9.9.tar.gz.sha256").write_text(f"{digest}  {archive.name}\n")
        result = ready.run("update", "--version", "v0.9.9")
        assert result.returncode == 1
        assert "not a valid Lineup package" in result.stderr

    def test_it_stops_when_the_backup_fails_before_touching_anything(self, ready):
        ready.seq("backup", 1)
        before = self.snapshot(ready)
        result = ready.run("update")
        assert result.returncode == 1
        assert "update was NOT started" in result.stderr
        assert "nothing was changed" in result.stderr
        assert self.snapshot(ready) == before
        assert not (ready.root / "previous").exists()
        for forbidden in (" pull", " up ", "alembic"):
            assert not ready.called(forbidden)

    def test_it_stops_when_the_database_state_cannot_be_read(self, ready):
        ready.flag("revision_fail")
        before = self.snapshot(ready)
        result = ready.run("update")
        assert result.returncode == 1
        assert "update was NOT started" in result.stderr
        assert self.snapshot(ready) == before
        assert not ready.called(" pull")

    def test_a_failed_start_with_the_database_unchanged_is_undone(self, ready):
        before = self.snapshot(ready)
        ready.seq("up", 1, 0)  # the new version fails to start; the old one starts again
        ready.seq("revision", "abc123", "abc123")
        result = ready.run("update")
        assert result.returncode == 1
        assert "did not start properly" in result.stderr
        assert "update was undone" in result.stderr
        assert "nothing was lost" in result.stderr
        assert self.snapshot(ready) == before
        assert ready.env_value("LINEUP_VERSION") == "v0.1.0"
        assert ready.docker_calls().count(
            next(c for c in ready.docker_calls() if " up -d" in c)
        ) == 2
        assert_no_secret(result)

    def test_a_pull_failure_is_undone_without_asking_the_database(self, ready):
        before = self.snapshot(ready)
        ready.seq("pull", 1)
        result = ready.run("update")
        assert result.returncode == 1
        assert "update was undone" in result.stderr
        assert self.snapshot(ready) == before
        # the database was only asked about once, before the update: `up` never ran, so nothing could change
        assert len([c for c in ready.docker_calls() if "alembic" in c]) == 1

    def test_a_failed_start_after_the_database_changed_is_left_alone_with_instructions(self, ready):
        ready.seq("up", 1)
        ready.seq("revision", "abc123", "def456")
        result = ready.run("update")
        assert result.returncode == 1
        today = time.strftime("%Y-%m-%d", time.gmtime())
        assert "changed the database" in result.stderr
        assert "NOT undone automatically" in result.stderr
        assert f"./lineup.sh restore --date {today}" in result.stderr
        assert "./lineup.sh update --version v0.1.0" in result.stderr
        # nothing was guessed: the new files and version stay, and nothing was started again
        assert ready.env_value("LINEUP_VERSION") == "v0.2.0"
        assert (ready.root / "compose.yml").read_text() == "# compose v0.2.0\n"
        assert len([c for c in ready.docker_calls() if " up -d" in c]) == 1
        assert not ready.called("pg_restore")

    def test_an_unreadable_revision_after_a_failed_start_is_treated_as_changed(self, ready):
        ready.seq("up", 1)
        ready.seq("revision", "abc123")
        # the first alembic call (before) works; afterwards it fails
        original = (ready.bin / "docker").read_text()
        _write_executable(
            ready.bin / "docker",
            original.replace(
                '[ -f "$FAKE_STATE/revision_fail" ] && exit 1',
                '[ -f "$FAKE_STATE/revision_fail" ] && exit 1\n      [ -f "$FAKE_STATE/seen_revision" ] && exit 1\n      touch "$FAKE_STATE/seen_revision"',
            ),
        )
        result = ready.run("update")
        assert result.returncode == 1
        assert "NOT undone automatically" in result.stderr

    def test_an_undone_update_whose_old_version_is_also_down_says_so(self, ready):
        ready.seq("up", 1, 1)
        ready.seq("revision", "abc123", "abc123")
        result = ready.run("update")
        assert result.returncode == 1
        assert "does not answer yet" in result.stderr
        assert "./lineup.sh restore --date" in result.stderr

    def test_the_old_version_is_not_restarted_when_the_health_check_fails_first(self, ready):
        ready.seq("health", 1, 0)
        ready.seq("revision", "abc123", "abc123")
        result = ready.run("update")
        assert result.returncode == 1
        assert "update was undone" in result.stderr

    def test_an_empty_database_revision_compares_equal(self, ready):
        ready.seq("up", 1, 0)
        _write_executable(
            ready.bin / "docker",
            (ready.bin / "docker").read_text().replace(
                'echo "$(next revision abc123) (head)"; exit 0', "exit 0"
            ),
        )
        result = ready.run("update")
        assert result.returncode == 1
        assert "update was undone" in result.stderr

    def test_unknown_options_are_refused(self, ready):
        assert ready.run("update", "--now").returncode == 2
        assert ready.run("update", "--version").returncode == 2


# --- status ------------------------------------------------------------------------------------


class TestStatus:
    def test_it_needs_an_installed_lineup(self, box):
        assert box.run("status").returncode == 1

    def test_a_healthy_install(self, box):
        box.write_env()
        box.flag("last_success", f"{int(time.time()) - 3 * 3600}\n")
        box.publish_release("v0.2.0")
        result = box.run("status")
        assert result.returncode == 0, result.stderr
        assert "api running" in result.stdout
        assert "Lineup answers and its database works" in result.stdout
        assert "Last successful backup: 3 hour(s) ago" in result.stdout
        assert "Installed version: v0.1.0" in result.stdout
        assert "A newer version exists: v0.2.0" in result.stdout
        assert "Free disk space on" in result.stdout
        assert_no_secret(result)

    def test_an_old_backup_is_a_warning(self, box):
        box.write_env()
        box.flag("last_success", f"{int(time.time()) - 40 * 3600}\n")
        result = box.run("status")
        assert result.returncode == 0
        assert "[ WARNING ]" in result.stdout
        assert "40 hour(s) ago" in result.stdout

    def test_no_backup_yet_is_a_warning(self, box):
        box.write_env()
        result = box.run("status")
        assert "No successful backup was found yet" in result.stdout
        assert "03:00 UTC" in result.stdout

    def test_an_unanswering_install_fails_with_advice(self, box):
        box.write_env()
        box.seq("health", 1)
        result = box.run("status")
        assert result.returncode == 1
        assert "Lineup does not answer" in result.stdout
        assert "What to do:" in result.stdout

    def test_the_current_version_is_reported_as_newest(self, box):
        box.write_env()
        box.publish_release("v0.1.0")
        assert "This is the newest version" in box.run("status").stdout

    def test_an_unreachable_release_list_is_not_an_error(self, box):
        box.write_env()
        result = box.run("status")
        assert "Could not check for a newer version" in result.stdout
        assert result.returncode == 0

    def test_low_disk_is_a_warning(self, box):
        box.write_env()
        result = box.run("status", FAKE_DF_KB="2097152")
        assert "only 2 GB" in result.stdout

    def test_unknown_options_are_refused(self, box):
        box.write_env()
        assert box.run("status", "--all").returncode == 2

    def test_hungarian_output(self, box):
        box.write_env(LINEUP_LANG="hu")
        result = box.run("status", lang=None)
        assert "Jelenlegi állapot" in result.stdout


# --- menu and entry point ----------------------------------------------------------------------


class TestMenu:
    def test_the_menu_runs_with_empty_input_and_changes_nothing(self, box):
        result = box.run(input="")
        assert result.returncode == 0
        for number in "123456":
            assert f"  {number}) " in result.stdout
        assert box.docker_calls() == []

    def test_the_menu_is_in_hungarian_by_default(self, box):
        result = box.run(input="0\n", lang=None)
        assert "Mit szeretne tenni?" in result.stdout

    def test_a_blank_line_and_zero_both_leave(self, box):
        assert box.run(input="\n").returncode == 0
        assert box.run(input="0\n").returncode == 0

    def test_a_choice_that_is_not_listed_is_explained(self, box):
        result = box.run(input="9\n")
        assert result.returncode == 2
        assert "not one of the choices" in result.stderr

    @pytest.mark.parametrize(
        ("choice", "expected"),
        [
            ("1", "Checking this machine"),
            ("6", "not installed"),
            ("4", "not installed"),
            ("3", "not installed"),
            ("5", "not installed"),
        ],
    )
    def test_every_menu_entry_runs_its_command(self, box, choice, expected):
        result = box.run(input=f"{choice}\n")
        assert expected in result.stdout + result.stderr

    def test_the_install_entry_runs_install(self, box):
        box.write_env()
        result = box.run(input="2\n")
        assert "already installed" in result.stderr

    def test_help_and_unknown_commands(self, box):
        assert "Usage: ./lineup.sh" in box.run("--help").stdout
        assert "Usage" in box.run("help").stdout
        result = box.run("explode")
        assert result.returncode == 2
        assert "Unknown command: explode" in result.stderr


# --- backup.sh ---------------------------------------------------------------------------------


class TestBackupScript:
    @pytest.fixture
    def backups(self, tmp_path):
        folder = tmp_path / "backups"
        folder.mkdir()
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_executable(bin_dir / "pg_dump", FAKE_PG_DUMP)
        return folder, bin_dir

    def run(self, backups, *args, **env):
        folder, bin_dir = backups
        return subprocess.run(  # noqa: S603
            ["bash", str(SELFHOST / "backup" / "backup.sh"), *args],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "BACKUPS_DIR": str(folder),
                **env,
            },
        )

    def calls(self, backups) -> list[str]:
        return (backups[0] / "pg_dump.calls").read_text().splitlines()

    def test_one_backup_writes_both_dumps_and_the_time(self, backups):
        result = self.run(backups, "--once")
        assert result.returncode == 0, result.stderr
        today = time.strftime("%Y-%m-%d", time.gmtime())
        folder = backups[0]
        assert (folder / f"lineup-{today}.dump").read_text() == "dump of lineup\n"
        assert (folder / f"auth-{today}.dump").read_text() == "dump of auth\n"
        assert abs(int((folder / "last-success").read_text()) - time.time()) < 60
        assert not list(folder.glob("*.tmp"))
        assert f"ok: {today}" in result.stdout

    def test_the_token_tables_are_left_out_of_the_auth_dump_only(self, backups):
        self.run(backups, "--once")
        lineup_call, auth_call = self.calls(backups)
        assert "--exclude-table-data" not in lineup_call
        for table in ("sessions", "refresh_tokens", "one_time_tokens", "flow_state"):
            assert f"--exclude-table-data=auth.{table}" in auth_call
        # rows that point at a session cannot be restored without it
        assert "--exclude-table-data=auth.mfa_amr_claims" in auth_call
        assert "-Fc" in lineup_call and "-Fc" in auth_call

    @pytest.mark.parametrize("failing", ["lineup", "auth"])
    def test_a_failure_leaves_no_half_backup_and_older_backups_alone(self, backups, failing):
        folder = backups[0]
        (folder / "lineup-2026-01-01.dump").write_text("old lineup")
        (folder / "auth-2026-01-01.dump").write_text("old auth")
        (folder / "last-success").write_text("111\n")
        result = self.run(backups, "--once", FAKE_FAIL_DB=failing)
        assert result.returncode == 1
        today = time.strftime("%Y-%m-%d", time.gmtime())
        assert not (folder / f"lineup-{today}.dump").exists()
        assert not (folder / f"auth-{today}.dump").exists()
        assert not list(folder.glob("*.tmp"))
        assert (folder / "lineup-2026-01-01.dump").read_text() == "old lineup"
        assert (folder / "last-success").read_text() == "111\n"
        output = result.stdout + result.stderr
        assert "FAILED" in output
        assert "SELECT" not in output and "SQL DETAIL" not in output

    def test_a_failed_backup_never_runs_retention(self, backups):
        folder = backups[0]
        ancient = folder / "lineup-2000-01-01.dump"
        ancient.write_text("old")
        os.utime(ancient, (0, 0))
        self.run(backups, "--once", FAKE_FAIL_DB="auth")
        assert ancient.exists()

    def test_old_dumps_are_deleted_after_a_success_and_recent_ones_kept(self, backups):
        folder = backups[0]
        old, recent = folder / "lineup-2000-01-01.dump", folder / "lineup-2999-01-01.dump"
        for path in (old, recent):
            path.write_text("x")
        os.utime(old, (0, 0))
        self.run(backups, "--once")
        assert not old.exists()
        assert recent.exists()
        assert (folder / "last-success").exists()

    def test_the_retention_days_can_be_changed(self, backups):
        folder = backups[0]
        stale = folder / "lineup-x.dump"
        stale.write_text("x")
        os.utime(stale, (time.time() - 3 * 86400,) * 2)
        self.run(backups, "--once", BACKUP_RETENTION_DAYS="1")
        assert not stale.exists()

    def test_a_safety_backup_has_its_own_name_and_never_replaces_the_daily_one(self, backups):
        folder = backups[0]
        today = time.strftime("%Y-%m-%d", time.gmtime())
        daily = folder / f"lineup-{today}.dump"
        daily.write_text("daily")
        result = self.run(backups, "--once", "--safety")
        assert result.returncode == 0
        assert daily.read_text() == "daily"
        assert list(folder.glob("lineup-safety-*.dump"))
        assert list(folder.glob("auth-safety-*.dump"))

    @pytest.mark.parametrize("hour", ["24", "abc", "-1", "100"])
    def test_a_bad_backup_hour_is_refused(self, backups, hour):
        result = self.run(backups, "--once", BACKUP_HOUR=hour)
        assert result.returncode == 2
        assert "BACKUP_HOUR" in result.stdout

    def test_an_unknown_argument_is_refused(self, backups):
        assert self.run(backups, "--now").returncode == 2

    def test_loop_mode_waits_for_the_hour_and_stops_cleanly_on_a_signal(self, backups):
        folder, bin_dir = backups
        process = subprocess.Popen(  # noqa: S603
            ["bash", str(SELFHOST / "backup" / "backup.sh")],  # noqa: S607
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "BACKUPS_DIR": str(folder),
                "BACKUP_HOUR": "03",
            },
        )
        time.sleep(1)
        assert process.poll() is None
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=10)
        assert process.returncode == 0
        assert "one backup every day at 03:00 UTC" in output
        assert not list(folder.glob("*.dump"))

    def test_the_loop_runs_a_backup_when_the_hour_arrives(self, backups):
        """With `sleep` replaced by a no-op the loop goes straight to a backup, and survives a failure."""
        folder, bin_dir = backups
        _write_executable(
            bin_dir / "sleep",
            f'#!/bin/bash\nn=$(cat "{folder}/slept" 2>/dev/null || echo 0)\n'
            f'echo $((n + 1)) > "{folder}/slept"\n'
            f'[ "$n" -ge 2 ] && kill -TERM "$PPID"\nexit 0\n',
        )
        process = subprocess.run(  # noqa: S603
            ["bash", str(SELFHOST / "backup" / "backup.sh")],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={
                "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                "BACKUPS_DIR": str(folder),
                "FAKE_FAIL_DB": "auth",
            },
        )
        assert process.returncode == 0
        assert process.stdout.count("FAILED") >= 1
        assert (folder / "slept").exists()
