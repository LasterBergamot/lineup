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


# ── the live smoke job (#190) ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def smoke_job(workflow) -> str:
    """The text of the `smoke:` job (it is the last job in the file)."""
    return workflow.split("\n  smoke:\n", 1)[1]


def test_every_action_is_pinned_to_a_sha(workflow):
    """The smoke job holds the database secret, so no action may move under it."""
    refs = re.findall(r"uses: (\S+)", workflow)
    assert refs
    assert all(re.search(r"@[0-9a-f]{40}$", ref) for ref in refs), refs


def test_smoke_runs_after_a_green_deploy_and_only_from_develop(smoke_job):
    """Pull request builds must never write to the shared database."""
    assert "needs: deploy" in smoke_job
    assert "if: github.ref == 'refs/heads/develop'" in smoke_job
    assert "pull_request" not in smoke_job


def test_smoke_job_reads_exactly_one_secret_through_env(smoke_job):
    assert re.findall(r"secrets\.([A-Z_]+)", smoke_job) == ["SMOKE_DATABASE_URL"]


def test_smoke_job_never_echoes_the_database_url(smoke_job):
    for line in smoke_job.splitlines():
        if line.strip().startswith(("echo", "printf", "set -x")):
            assert "$DATABASE_URL" not in line and "${DATABASE_URL" not in line
    assert "set -x" not in smoke_job
    assert "env\n" not in smoke_job


def test_smoke_job_uses_the_shared_script_and_localhost_only(smoke_job):
    assert "scripts/smoke_live.py" in smoke_job
    assert "scripts/smoke_auth.py" in smoke_job
    assert "--host 127.0.0.1" in smoke_job
    assert "--no-access-log" in smoke_job
    assert "SUPABASE_URL=http://127.0.0.1:" in smoke_job


def test_smoke_job_removes_its_tokens_and_is_not_cancelled(workflow, smoke_job):
    assert "rm -f" in smoke_job and ".jwt" in smoke_job
    assert "cancel-in-progress: false" in workflow
