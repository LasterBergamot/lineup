"""Guards on .github/workflows/deploy-dev.yml, the CD workflow for the dev API (#8)."""

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-dev.yml"
FLY_TOML = ROOT / "backend" / "fly.toml"


@pytest.fixture(scope="module")
def workflow() -> str:
    """The workflow file as text (no YAML parser is a dependency)."""
    return WORKFLOW.read_text()


def test_deploys_the_app_named_in_fly_toml(workflow):
    app = tomllib.loads(FLY_TOML.read_text())["app"]
    assert f"FLY_APP: {app}\n" in workflow


def test_deploys_a_single_machine(workflow):
    """Without --ha=false Fly adds a second machine and the in-memory rate limit breaks."""
    assert "flyctl deploy --ha=false" in workflow


def test_runs_only_on_develop(workflow):
    assert "branches: [develop]" in workflow
    assert "main" not in re.findall(r"branches: \[(.*?)\]", workflow)


def test_secrets_are_only_read_through_env(workflow):
    """A secret in a `run:` line could be echoed; `env:` keeps it masked."""
    for line in workflow.splitlines():
        if "secrets." in line:
            assert re.match(r"\s+[A-Z_]+: \$\{\{ secrets\.[A-Z_]+ \}\}$", line), line


def test_third_party_action_is_pinned_to_a_sha(workflow):
    refs = re.findall(r"uses: (superfly/\S+)", workflow)
    assert refs
    assert all(re.search(r"@[0-9a-f]{40}$", ref) for ref in refs)


def test_never_cancels_a_running_deploy(workflow):
    assert "cancel-in-progress: false" in workflow


def test_checks_health_including_the_database(workflow):
    assert "/health?db=1" in workflow
