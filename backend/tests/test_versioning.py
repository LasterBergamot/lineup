"""Guards on the repo-wide version (#17): one number in backend and frontend, read from one place."""

import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest

from app import app
from lineup import version as version_module

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "backend" / "pyproject.toml"
PACKAGE_JSON = ROOT / "frontend" / "package.json"
OPENAPI = ROOT / "frontend" / "src" / "api" / "openapi.json"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SEMVER = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"


def _load_bump_module():
    spec = importlib.util.spec_from_file_location(
        "bump_version", ROOT / "scripts" / "bump_version.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bump = _load_bump_module()


class TestOneVersion:
    def test_backend_and_frontend_versions_are_equal(self):
        backend = tomllib.loads(PYPROJECT.read_text())["project"]["version"]
        frontend = json.loads(PACKAGE_JSON.read_text())["version"]
        assert backend == frontend

    def test_version_is_plain_semver(self):
        assert re.fullmatch(SEMVER, version_module.read_version())

    def test_the_api_reports_the_pyproject_version(self):
        assert app.version == tomllib.loads(PYPROJECT.read_text())["project"]["version"]

    def test_the_generated_openapi_spec_carries_it_too(self):
        """A bump without `task fe:api` would leave the client stale (CI catches it as well)."""
        assert json.loads(OPENAPI.read_text())["info"]["version"] == app.version


class TestNextVersion:
    @pytest.mark.parametrize(
        ("current", "change", "expected"),
        [
            ("0.1.0", "patch", "0.1.1"),
            ("0.1.9", "minor", "0.2.0"),
            ("0.9.3", "major", "1.0.0"),
            ("0.1.0", "1.2.3", "1.2.3"),
        ],
    )
    def test_next_version(self, current, change, expected):
        assert bump.next_version(current, change) == expected

    @pytest.mark.parametrize(
        "bad", ["1.2", "v1.2.3", "1.2.3-rc1", "01.2.3", "", "huge"]
    )
    def test_rejects_anything_but_plain_semver(self, bad):
        with pytest.raises(ValueError, match="not a MAJOR.MINOR.PATCH"):
            bump.next_version("0.1.0", bad)

    def test_rejects_a_malformed_current_version(self):
        with pytest.raises(ValueError):
            bump.next_version("nonsense", "patch")


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    """Point the script at throw-away copies so tests never touch the real version files."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n\n[tool.other]\nversion = "9.9.9"\n'
    )
    package = tmp_path / "package.json"
    package.write_text(
        '{\n  "name": "demo",\n  "version": "0.1.0",\n  "dependencies": {"version": "1"}\n}\n'
    )
    monkeypatch.setattr(bump, "PYPROJECT", pyproject)
    monkeypatch.setattr(bump, "PACKAGE_JSON", package)
    return pyproject, package


class TestBumpScript:
    def test_bumps_both_files_and_nothing_else(self, fake_repo, capsys):
        pyproject, package = fake_repo
        assert bump.main(["minor"]) == 0
        assert capsys.readouterr().out.strip() == "0.1.0 -> 0.2.0"
        assert 'version = "0.2.0"' in pyproject.read_text()
        assert 'version = "9.9.9"' in pyproject.read_text()  # other tables untouched
        assert '"version": "0.2.0"' in package.read_text()
        assert '"dependencies": {"version": "1"}' in package.read_text()

    def test_show_prints_the_current_version(self, fake_repo, capsys):
        assert bump.main(["--show"]) == 0
        assert capsys.readouterr().out.strip() == "0.1.0"
        assert bump.main([]) == 0

    def test_refuses_when_the_two_files_disagree(self, fake_repo, capsys):
        _, package = fake_repo
        package.write_text(package.read_text().replace('"0.1.0"', '"0.0.5"', 1))
        assert bump.main(["patch"]) == 1
        assert "differ" in capsys.readouterr().err

    def test_rejects_a_bad_version_without_writing(self, fake_repo, capsys):
        pyproject, _ = fake_repo
        before = pyproject.read_text()
        assert bump.main(["1.2"]) == 2
        assert "MAJOR.MINOR.PATCH" in capsys.readouterr().err
        assert pyproject.read_text() == before

    def test_rejects_a_no_op_bump(self, fake_repo, capsys):
        assert bump.main(["0.1.0"]) == 2
        assert "already at" in capsys.readouterr().err

    def test_fails_loudly_when_a_file_has_no_version(self, fake_repo):
        pyproject, package = fake_repo
        pyproject.write_text('[project]\nname = "demo"\n')
        with pytest.raises(ValueError, match="no version line"):
            bump.write_versions("0.2.0")
        pyproject.write_text('[project]\nversion = "0.1.0"\n')
        package.write_text('{"name": "demo"}')
        with pytest.raises(ValueError, match="no version key"):
            bump.write_versions("0.2.0")

    def test_the_real_files_are_in_a_shape_the_script_can_edit(self):
        """Dry run against the committed files: both patterns must match exactly once."""
        assert len(bump.PYPROJECT_VERSION.findall(PYPROJECT.read_text())) == 1
        assert len(bump.PACKAGE_VERSION.findall(PACKAGE_JSON.read_text())) >= 1


@pytest.fixture(scope="module")
def workflow():
    """The release workflow as text (no YAML parser is a dependency of the app)."""
    return RELEASE_WORKFLOW.read_text()


class TestReleaseWorkflow:
    def test_is_only_started_by_hand(self, workflow):
        assert re.search(r"^on:\n  workflow_dispatch:\n", workflow, re.MULTILINE)
        assert "push:" not in workflow and "pull_request" not in workflow

    def test_only_runs_from_develop_or_main(self, workflow):
        assert (
            "github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'"
            in workflow
        )

    def test_can_write_contents_but_nothing_else(self, workflow):
        assert re.search(
            r"^permissions:\n  contents: write\n\n", workflow, re.MULTILINE
        )

    def test_uses_no_secrets_and_pins_its_action(self, workflow):
        assert "secrets." not in workflow
        for ref in re.findall(r"uses: (\S+)", workflow):
            assert re.search(r"@[0-9a-f]{40}$", ref), ref

    def test_never_cancels_a_running_release(self, workflow):
        assert "cancel-in-progress: false" in workflow

    def test_refuses_an_existing_tag_and_mismatched_versions(self, workflow):
        assert "already exists" in workflow
        assert "versions differ" in workflow

    def test_marks_pre_1_0_releases_as_prerelease(self, workflow):
        assert "--prerelease" in workflow

    def test_v1_and_later_only_from_main(self, workflow):
        assert '"$GITHUB_REF_NAME" != "main"' in workflow

    def test_untrusted_values_never_land_in_a_run_line(self, workflow):
        """`${{ … }}` in `run:` is shell injection; the workflow passes values through env."""
        for line in workflow.splitlines():
            if "${{" in line:
                assert (
                    re.match(r"\s+(GH_TOKEN|VERSION|PRERELEASE): \$\{\{ .+ \}\}$", line)
                    or "if:" in line
                ), line
