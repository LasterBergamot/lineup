"""Guards on repo hygiene files: ignore patterns, the security policy, CodeQL and Claude's secret
deny list (#98). They keep personal data and secrets out of commits and images."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "pattern",
    [
        ".env.*",  # also covers backend/.env.migrate and frontend/.env.production
        "!.env.example",  # the documented templates stay committed
        "*.db",
        "*.sqlite",
        "backend/resources/modified_rajtlista.docx",  # `task run` output: a filled-in lineup
    ],
)
def test_local_state_and_secrets_are_git_ignored(pattern):
    """Checked as text (a `git check-ignore` call would need a new ruff `S` ignore); the
    patterns were also verified once with `git check-ignore -v` for each path."""
    assert pattern in (ROOT / ".gitignore").read_text().splitlines()


def test_the_docker_context_excludes_secrets_databases_and_the_demo_output():
    lines = (ROOT / "backend" / ".dockerignore").read_text().splitlines()
    for pattern in (
        ".env",
        ".env.*",
        "*.db",
        "*.sqlite",
        "resources/modified_rajtlista.docx",
    ):
        assert pattern in lines


def test_claude_may_not_read_any_env_file_of_the_frontend():
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
    denied = settings["permissions"]["deny"]
    for name in (".env", ".env.local", ".env.production", ".env.development"):
        assert f"Read(./frontend/{name})" in denied


def test_security_policy_points_at_private_reporting():
    policy = (ROOT / "SECURITY.md").read_text()
    assert "github.com/LasterBergamot/lineup/security/advisories/new" in policy
    assert "not in a public issue" in policy


class TestCodeqlWorkflow:
    @pytest.fixture
    def workflow(self) -> str:
        return (ROOT / ".github" / "workflows" / "codeql.yml").read_text()

    def test_analyzes_pull_requests_into_develop_and_main(self, workflow):
        pull_request = workflow.split("pull_request:", 1)[1].split("push:", 1)[0]
        assert "branches: [main, develop]" in pull_request

    def test_covers_both_languages_of_the_repo(self, workflow):
        assert "language: [python, javascript-typescript]" in workflow

    def test_token_is_read_only_except_for_the_upload(self, workflow):
        top_level = workflow.split("\njobs:", 1)[0]
        assert "security-events" not in top_level
        assert workflow.count("security-events: write") == 1

    def test_skips_dependabot_whose_token_cannot_upload(self, workflow):
        assert "github.actor != 'dependabot[bot]'" in workflow

    def test_every_action_is_pinned_to_a_commit_sha(self, workflow):
        refs = re.findall(r"uses:\s*(\S+)", workflow)
        assert refs
        assert all(re.search(r"@[0-9a-f]{40}$", ref) for ref in refs)
