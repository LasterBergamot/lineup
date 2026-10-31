"""Tests for scripts/doctor.sh (`task doctor`), the prerequisite check behind documentation/Setup.md.

Each test runs the script with a PATH that holds only fake tools (plus the `grep` and `head` it
needs), so the result never depends on what the machine running the tests has installed.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

DOCTOR = Path(__file__).resolve().parents[2] / "scripts" / "doctor.sh"

READY = {
    "python3": "Python 3.13.2",
    "uv": "uv 0.12.0",
    "task": "Task version: v3.54.0",
    "docker": "Docker version 29.0.1, build abc",
    "docker compose": "Docker Compose version v2.24.0",
}


def _write_tool(bin_dir: Path, name: str, outputs: dict[str, str]) -> None:
    """A fake `name` that prints outputs[first-arg] (docker answers `--version` and `compose`)."""
    cases = "\n".join(f'  "{arg}") echo "{text}" ;;' for arg, text in outputs.items())
    script = bin_dir / name
    script.write_text(f'#!/bin/sh\ncase "$1" in\n{cases}\n  *) exit 1 ;;\nesac\n')
    script.chmod(0o755)


def _run(
    tmp_path: Path, tools: dict[str, str], task_name: str = "task"
) -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for helper in ("grep", "head"):
        os.symlink(shutil.which(helper), bin_dir / helper)
    docker = {}
    for name, text in tools.items():
        if name == "docker":
            docker["--version"] = text
        elif name == "docker compose":
            docker["compose"] = text
        else:
            _write_tool(
                bin_dir, task_name if name == "task" else name, {"--version": text}
            )
    if docker:
        _write_tool(bin_dir, "docker", docker)
    # Fixed argv (bash + this repo's script), no shell; the only input is the fake PATH.
    return subprocess.run(  # noqa: S603
        [shutil.which("bash"), str(DOCTOR)],
        env={"PATH": str(bin_dir)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_ready_machine_passes(tmp_path):
    result = _run(tmp_path, READY)
    assert result.returncode == 0, result.stdout
    assert "ok    python3         3.13.2" in result.stdout
    assert "ok    docker compose  2.24.0" in result.stdout
    assert "All required tools are present." in result.stdout


def test_missing_optional_tools_are_only_reported(tmp_path):
    result = _run(tmp_path, READY)
    assert result.returncode == 0
    for name in ("node", "pnpm", "gh", "yamllint", "actionlint", "lazydocker"):
        assert f"skip  {name}" in result.stdout


def test_missing_required_tool_fails(tmp_path):
    tools = {k: v for k, v in READY.items() if k != "uv"}
    result = _run(tmp_path, tools)
    assert result.returncode == 1
    assert "FAIL  uv              not found (required)" in result.stdout
    assert "README.md, section Prerequisites" in result.stdout


@pytest.mark.parametrize(
    ("tool", "text", "expected"),
    [
        ("python3", "Python 3.12.9", "FAIL  python3         3.12.9 is older than 3.13"),
        # Numeric, not string, comparison: 3.9 is older than 3.13.
        ("python3", "Python 3.9.0", "FAIL  python3         3.9.0 is older than 3.13"),
        (
            "docker compose",
            "Docker Compose version v2.23.3",
            "FAIL  docker compose  2.23.3 is older than 2.24",
        ),
    ],
)
def test_too_old_required_tool_fails(tmp_path, tool, text, expected):
    result = _run(tmp_path, {**READY, tool: text})
    assert result.returncode == 1
    assert expected in result.stdout


def test_newer_major_version_passes(tmp_path):
    result = _run(
        tmp_path,
        {
            **READY,
            "python3": "Python 4.0",
            "docker compose": "Docker Compose version 5.6.1",
        },
    )
    assert result.returncode == 0, result.stdout


def test_go_task_binary_is_accepted(tmp_path):
    # Arch Linux ships Task as `go-task`; the alias to `task` doesn't reach scripts.
    result = _run(tmp_path, READY, task_name="go-task")
    assert result.returncode == 0, result.stdout
    assert "ok    task            3.54.0" in result.stdout


def test_version_without_number_is_treated_as_too_old(tmp_path):
    result = _run(tmp_path, {**READY, "python3": "Python (custom build)"})
    assert result.returncode == 1
    assert "FAIL  python3         unknown is older than 3.13" in result.stdout
