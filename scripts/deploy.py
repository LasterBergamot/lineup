#!/usr/bin/env python3
"""Deploy Lineup to the cloud dev API, or update the self-hosted machine (#258).

Usage: task deploy [-- --cloud|--local] [--version vX.Y.Z] [--yes]

Nothing runs without a target and a typed `yes`. With no target, a terminal gets a menu; without a
terminal the script stops with a usage error (exit 2), so a script or CI job never deploys by accident.
`--cloud` starts `deploy-dev.yml` on `develop` through the GitHub CLI and waits for it. `--local` runs
`./lineup.sh update` on the self-hosted machine over SSH. Its settings come from `LINEUP_SELFHOST_SSH`
and `LINEUP_SELFHOST_DIR`, or from `~/.config/lineup/selfhost.env`, which is read as data and never
executed. The host and the paths are never printed, because the repo and its logs are public.

Exit codes: 0 done, 1 aborted or failed, 2 usage error.
"""

import argparse
import os
import re
import shlex
import stat
import subprocess
import sys
import time
from pathlib import Path

WORKFLOW = "deploy-dev.yml"
BRANCH = "develop"
SETTINGS = ("LINEUP_SELFHOST_SSH", "LINEUP_SELFHOST_DIR")
# `lineup.sh update` only knows release tags, so only those are passed through to the machine.
VERSION = re.compile(r"v\d+\.\d+\.\d+")
# `gh run list` does not show a run started a moment ago, so wait before looking for its id.
RUN_LOOKUP_DELAY_SECONDS = 5
ABORTED = "Aborted: nothing was changed."
EXIT_FAILED = 1
EXIT_USAGE = 2


class SettingsError(Exception):
    """The self-hosted settings are missing or unsafe. The message says what to do and never holds a value."""


def settings_file() -> Path:
    """Return `~/.config/lineup/selfhost.env`, resolved when called so tests can point HOME elsewhere."""
    return Path.home() / ".config" / "lineup" / "selfhost.env"


def parse_env_file(text: str) -> dict[str, str]:
    """Read the `KEY=VALUE` lines of the settings file as plain data, keeping only SETTINGS.

    Blank lines, `#` comments and lines without `=` are skipped. A value wrapped in matching quotes
    loses them. Nothing is expanded or executed, so `$(...)` stays the literal text it was written as.
    """
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key.strip() in SETTINGS:
            values[key.strip()] = value
    return values


def local_settings(environ: dict[str, str], path: Path) -> tuple[str, str]:
    """Return `(ssh_target, remote_dir)`: each from the environment, else from the settings file.

    The file is only opened when the environment lacks a value, and only then must it be mode 600.
    Raises `SettingsError` when a value is missing, the file is not private, or the SSH target starts
    with `-` (ssh would read it as an option, e.g. `-oProxyCommand=...`, which runs a command).
    """
    values = {key: environ[key] for key in SETTINGS if environ.get(key)}
    if len(values) < len(SETTINGS) and path.exists():
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise SettingsError(
                "~/.config/lineup/selfhost.env must be mode 600 (run chmod 600 on it), "
                "because it holds the machine's settings."
            )
        for key, value in parse_env_file(path.read_text()).items():
            values.setdefault(key, value)
    missing = [key for key in SETTINGS if not values.get(key)]
    if missing:
        raise SettingsError(
            f"Missing {' and '.join(missing)}. Set them in the environment or in "
            "~/.config/lineup/selfhost.env, following self-host-plan.md M2, or run "
            "./lineup.sh update on the machine itself."
        )
    ssh_target, remote_dir = values[SETTINGS[0]], values[SETTINGS[1]]
    if ssh_target.startswith("-"):
        raise SettingsError(
            "LINEUP_SELFHOST_SSH must not start with '-': ssh would read it as an option."
        )
    return ssh_target, remote_dir


def remote_command(remote_dir: str, version: str | None) -> str:
    """Return the shell line run on the machine: enter the install folder and update it.

    The folder and the version are quoted, so nothing in them can add a command.
    """
    command = f"cd {shlex.quote(remote_dir)} && ./lineup.sh update"
    if version:
        command += f" --version {shlex.quote(version)}"
    return command


def confirm(question: str, assume_yes: bool) -> bool:
    """Print what will happen and return True only for a typed `yes` (or with `--yes`).

    End of input counts as no, so an unattended run without `--yes` changes nothing.
    """
    if assume_yes:
        return True
    print(question, file=sys.stderr)
    try:
        answer = input("Type 'yes' to continue: ")
    except EOFError:
        print(
            "No terminal to ask on; pass --yes to run without asking.", file=sys.stderr
        )
        return False
    return answer.strip().lower() == "yes"


def choose_target() -> str | None:
    """Ask on a terminal which target to use; return `cloud`, `local`, or None for no clear answer."""
    print(
        "Deploy where?\n"
        "  1) cloud: the dev API on Fly.io, through GitHub Actions\n"
        "  2) local: the self-hosted machine",
        file=sys.stderr,
    )
    try:
        answer = input("Choose 1 or 2: ").strip()
    except EOFError:
        return None
    return {"1": "cloud", "2": "local"}.get(answer)


def deploy_cloud() -> int:
    """Start `deploy-dev.yml` on develop, wait for it and return its exit status.

    A normal push to develop still deploys by itself; this is for a deliberate manual run.
    A missing `gh` is reported in words rather than as a traceback.
    """
    try:
        started = subprocess.run(
            ["gh", "workflow", "run", WORKFLOW, "--ref", BRANCH], check=False
        )
        if started.returncode != 0:
            print(
                "GitHub did not start the workflow. Check `gh auth status`.",
                file=sys.stderr,
            )
            return EXIT_FAILED
        time.sleep(RUN_LOOKUP_DELAY_SECONDS)
        listed = subprocess.run(
            [
                "gh",
                "run",
                "list",
                f"--workflow={WORKFLOW}",
                "--branch",
                BRANCH,
                "--limit",
                "1",
                "--json",
                "databaseId",
                "--jq",
                ".[0].databaseId",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        run_id = listed.stdout.strip()
        if listed.returncode != 0 or not run_id.isdigit():
            print(
                "The workflow started, but its run could not be found. See the Actions tab.",
                file=sys.stderr,
            )
            return EXIT_FAILED
        print(f"Watching run {run_id} until it finishes ...")
        watched = subprocess.run(
            ["gh", "run", "watch", run_id, "--exit-status"], check=False
        )
        return watched.returncode
    except FileNotFoundError:
        print(
            "The GitHub CLI (gh) is not installed. Install it from https://cli.github.com "
            "and run `gh auth login`.",
            file=sys.stderr,
        )
        return EXIT_FAILED


def deploy_local(ssh_target: str, remote_dir: str, version: str | None) -> int:
    """Run the update on the machine over SSH and return ssh's exit status.

    The argument list (never `shell=True`) keeps the target and the command apart. `--` comes
    before the target, not after it: BSD getopt (macOS) stops at the first operand, so a `--` placed
    after the host would be sent to the machine as part of the command. The target was also checked
    not to start with `-`.
    """
    command = ["ssh", "--", ssh_target, remote_command(remote_dir, version)]
    try:
        result = subprocess.run(command, check=False)
    except FileNotFoundError:
        print("ssh is not installed on this computer.", file=sys.stderr)
        return EXIT_FAILED
    if result.returncode != 0:
        print(
            "The update did not finish. The messages above say what to do next.",
            file=sys.stderr,
        )
    return result.returncode


def version_tag(value: str) -> str:
    """argparse type for `--version`: only `vX.Y.Z` release tags are accepted."""
    if not VERSION.fullmatch(value):
        raise argparse.ArgumentTypeError("expected a release tag such as v1.2.3")
    return value


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code (see the module docstring)."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0], prog="task deploy"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--cloud", action="store_true", help="start the cloud deploy (GitHub Actions)"
    )
    group.add_argument(
        "--local", action="store_true", help="update the self-hosted machine over SSH"
    )
    parser.add_argument(
        "--version",
        type=version_tag,
        metavar="vX.Y.Z",
        help="with --local: update to this release instead of the newest",
    )
    parser.add_argument(
        "--yes", action="store_true", help="skip the typed confirmation"
    )
    args = parser.parse_args(argv)

    target = "cloud" if args.cloud else "local" if args.local else None
    if target is None:
        if not sys.stdin.isatty():
            print(
                "No target given. Run `task deploy -- --cloud` or `task deploy -- --local`.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        target = choose_target()
        if target is None:
            print(ABORTED, file=sys.stderr)
            return EXIT_FAILED
    if args.version and target == "cloud":
        print(
            "--version only applies to --local: the cloud deploy always runs develop.",
            file=sys.stderr,
        )
        return EXIT_USAGE

    if target == "local":
        try:
            ssh_target, remote_dir = local_settings(dict(os.environ), settings_file())
        except SettingsError as error:
            print(error, file=sys.stderr)
            return EXIT_FAILED
        what = (
            f"update the self-hosted machine to {args.version}"
            if args.version
            else "update the self-hosted machine to the newest release"
        )
        question = f"Will {what} over SSH with ./lineup.sh update. It takes a backup first and stops if that fails."
    else:
        question = "Will start the deploy-dev workflow on develop in GitHub Actions: it migrates the dev database and deploys the dev API."

    if not confirm(question, args.yes):
        print(ABORTED, file=sys.stderr)
        return EXIT_FAILED
    if target == "local":
        return deploy_local(ssh_target, remote_dir, args.version)
    return deploy_cloud()


if __name__ == "__main__":
    sys.exit(main())
