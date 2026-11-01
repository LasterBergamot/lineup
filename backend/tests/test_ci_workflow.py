"""Guards on the repo's GitHub Actions workflows: pinned actions everywhere, and the CI workflow's
token permissions, concurrency and lockfile checks (#61)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
CI = ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def ci() -> str:
    """ci.yml as text (no YAML parser is a dependency)."""
    return CI.read_text()


def test_there_are_workflows_to_check():
    assert CI in WORKFLOWS


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit_sha(workflow):
    """A tag can be moved to different code; a commit SHA cannot. Dependabot keeps the
    `# vX` comment and the SHA current together."""
    refs = re.findall(r"^\s*(?:-\s+)?uses:\s*(\S+)", workflow.read_text(), re.MULTILINE)
    unpinned = [
        ref
        for ref in refs
        if not ref.startswith("./") and not re.search(r"@[0-9a-f]{40}$", ref)
    ]
    assert not unpinned


def test_the_token_is_read_only_by_default(ci):
    top_level = ci.split("\njobs:", 1)[0]
    assert re.search(r"^permissions:\n  contents: read$", top_level, re.MULTILINE)


def test_only_the_e2e_job_may_write_security_events(ci):
    assert ci.count("security-events: write") == 1
    e2e_job = ci.split("\n  e2e:", 1)[1]
    assert "security-events: write" in e2e_job


def test_a_new_push_cancels_an_older_pull_request_run_only(ci):
    assert "group: ${{ github.workflow }}-${{ github.ref }}" in ci
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in ci


def test_python_dependencies_are_installed_from_a_checked_lockfile(ci):
    """`--frozen` trusts uv.lock blindly; `--locked` fails when it no longer matches pyproject."""
    assert "uv sync --frozen" not in ci
    assert "uv sync --locked" in ci


def test_trivy_runs_once_and_the_upload_needs_a_result_file(ci):
    assert ci.count("aquasecurity/trivy-action@") == 1
    upload = ci.split("Upload Trivy results", 1)[1]
    assert "hashFiles('trivy-results.sarif')" in upload
    assert "always()" not in upload


def test_workflow_files_are_linted(ci):
    assert "rhysd/actionlint@sha256:" in ci
    assert "yamllint" in ci
