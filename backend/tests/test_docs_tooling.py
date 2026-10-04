"""Tests for the repo-level docs tooling in ../scripts and the wiki-sync page map."""

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def _load_references_module():
    spec = importlib.util.spec_from_file_location(
        "docs_references", SCRIPTS / "docs_references.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


refs = _load_references_module()

PYPROJECT = """
[project]
name = "demo"
dependencies = ["FastAPI>=0.1", "uvicorn[standard]>=0.5", "Some_Pkg>=1"]

[dependency-groups]
dev = ["pytest>=9"]
"""

LOCK = """
[[package]]
name = "fastapi"
version = "1.2.3"

[[package]]
name = "uvicorn"
version = "0.5.1"

[[package]]
name = "pytest"
version = "9.0.0"
"""

DOCKERFILE = """FROM python:3.13-slim AS base
# a comment that mentions apt-get install nothing
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        libreoffice \\
        fonts-foo \\
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
COPY --from=someorg/tool:1 /x /x
COPY --from=builder /a /a
FROM $BASE_IMAGE
"""

WORKFLOW = """jobs:
  a:
    steps:
      - uses: actions/checkout@v7
      - uses: github/codeql-action/upload-sarif@v4
      - uses: ./local-action
      - uses: actions/checkout@v6
"""

PAGE = f"# References\n\nhandwritten\n\n{refs.BEGIN}\nold\n{refs.END}\n\ntail\n"


@pytest.fixture
def fake_root(tmp_path: Path) -> Path:
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend/pyproject.toml").write_text(PYPROJECT)
    (tmp_path / "backend/uv.lock").write_text(LOCK)
    (tmp_path / "backend/Dockerfile").write_text(DOCKERFILE)
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text(WORKFLOW)
    (tmp_path / "documentation").mkdir()
    (tmp_path / "documentation/References.md").write_text(PAGE)
    return tmp_path


class TestDocsReferences:
    def test_python_packages_normalise_names_and_include_dev_group(self, fake_root):
        assert refs.python_packages(fake_root) == [
            ("fastapi", "runtime"),
            ("pytest", "dev"),
            ("some-pkg", "runtime"),
            ("uvicorn", "runtime"),
        ]

    def test_npm_packages_empty_without_frontend(self, fake_root):
        assert refs.npm_packages(fake_root) == []

    def test_npm_packages_read_from_package_json(self, fake_root):
        (fake_root / "frontend").mkdir()
        (fake_root / "frontend/package.json").write_text(
            '{"dependencies": {"react": "^19.0.0"}, "devDependencies": {"vite": "^7.0.0"}}'
        )
        assert refs.npm_packages(fake_root) == [("react", "runtime"), ("vite", "dev")]

    def test_docker_images_drop_tags_and_digests_and_skip_comments_and_build_args(
        self, fake_root
    ):
        (fake_root / "backend/Dockerfile").write_text(
            DOCKERFILE + "FROM debian@sha256:abc\n"
        )
        assert refs.docker_images(fake_root) == [
            "builder",
            "debian",
            "ghcr.io/astral-sh/uv",
            "python",
            "someorg/tool",
        ]

    def test_apt_packages_follow_line_continuations(self, fake_root):
        assert refs.apt_packages(fake_root) == ["fonts-foo", "libreoffice"]

    def test_github_actions_are_deduplicated_and_local_ones_skipped(self, fake_root):
        assert refs.github_actions(fake_root) == [
            "actions/checkout",
            "github/codeql-action",
        ]

    @pytest.mark.parametrize(
        ("image", "expected"),
        [
            ("python:3.13-slim", "https://hub.docker.com/_/python"),
            ("someorg/tool:1", "https://hub.docker.com/r/someorg/tool"),
            ("ghcr.io/astral-sh/uv:latest", "https://github.com/astral-sh/uv"),
        ],
    )
    def test_image_link(self, image, expected):
        assert refs._image_link(image) == expected

    def test_render_includes_every_section_and_markers(self, fake_root):
        (fake_root / "frontend").mkdir()
        (fake_root / "frontend/package.json").write_text(
            '{"dependencies": {"react": "^19.0.0"}}'
        )
        block = refs.render(fake_root)
        assert block.startswith(refs.BEGIN) and block.endswith(refs.END)
        for expected in (
            "### Python packages",
            "### npm packages",
            "### Container image",
            "### GitHub Actions",
        ):
            assert expected in block
        assert "https://pypi.org/project/fastapi/" in block
        assert "https://www.npmjs.com/package/react" in block

    def test_render_omits_npm_section_without_frontend(self, fake_root):
        assert "### npm packages" not in refs.render(fake_root)

    def test_apply_block_keeps_handwritten_text(self, fake_root):
        result = refs.apply_block(PAGE, f"{refs.BEGIN}\nnew\n{refs.END}")
        assert result.startswith("# References\n\nhandwritten\n\n")
        assert result.endswith("\n\ntail\n")
        assert "old" not in result and "new" in result

    @pytest.mark.parametrize("page", ["no markers", f"{refs.END} {refs.BEGIN}"])
    def test_apply_block_requires_markers_in_order(self, page):
        with pytest.raises(ValueError, match="markers"):
            refs.apply_block(page, "x")

    def test_write_then_check_passes_and_stale_check_fails(self, fake_root, capsys):
        assert refs.main(["--check", "--root", str(fake_root)]) == 1
        assert "out of date" in capsys.readouterr().err

        assert refs.main(["--write", "--root", str(fake_root)]) == 0
        assert refs.main(["--check", "--root", str(fake_root)]) == 0
        assert "up to date" in capsys.readouterr().out

        (fake_root / "backend/uv.lock").write_text(LOCK.replace("9.0.0", "9.1.0"))
        assert refs.main(["--check", "--root", str(fake_root)]) == 0, (
            "version bumps must not make the page stale"
        )

        (fake_root / "backend/pyproject.toml").write_text(
            PYPROJECT.replace('"pytest>=9"', '"pytest>=9", "ruff>=1"')
        )
        assert refs.main(["--check", "--root", str(fake_root)]) == 1, (
            "a new dependency must"
        )

    def test_repo_references_page_is_up_to_date(self):
        """Fails when a dependency changes without running `task docs:references`."""
        assert refs.main(["--check"]) == 0


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)  # noqa: S603, S607


def _commit(repo: Path, **files: str) -> None:
    for name, content in files.items():
        path = repo / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "c")


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "base")
    _commit(tmp_path, **{"README.md": "x"})
    _git(tmp_path, "checkout", "-b", "feature")
    return tmp_path


def _run_check(repo: Path, labels: str = "") -> subprocess.CompletedProcess:
    env = {**os.environ, "PR_LABELS": labels}
    return subprocess.run(  # noqa: S603
        [str(SCRIPTS / "check_docs_touched.sh"), "base", "HEAD"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


class TestCheckDocsTouched:
    def test_passes_when_nothing_code_related_changed(self, git_repo):
        _commit(git_repo, **{"notes.txt": "x"})
        result = _run_check(git_repo)
        assert result.returncode == 0
        assert "nothing to document" in result.stdout

    def test_fails_when_code_changes_without_docs(self, git_repo):
        _commit(git_repo, **{"backend__lineup__x.py": "x = 1"})
        result = _run_check(git_repo)
        assert result.returncode == 1
        assert "backend/lineup/x.py" in result.stderr
        assert "no-docs" in result.stderr

    @pytest.mark.parametrize(
        "docs_file", ["README.md", "CLAUDE.md", "documentation__Home.md"]
    )
    def test_passes_when_docs_change_alongside_code(self, git_repo, docs_file):
        _commit(git_repo, **{"Taskfile.yml": "x", docs_file: "changed"})
        result = _run_check(git_repo)
        assert result.returncode == 0
        assert "both changed" in result.stdout

    def test_no_docs_label_skips_the_check(self, git_repo):
        _commit(git_repo, **{"backend__lineup__x.py": "x = 1"})
        result = _run_check(git_repo, labels="bug,no-docs")
        assert result.returncode == 0
        assert "skipping" in result.stdout

    def test_similar_label_does_not_skip_the_check(self, git_repo):
        _commit(git_repo, **{"backend__lineup__x.py": "x = 1"})
        assert _run_check(git_repo, labels="no-docs-needed").returncode == 1


class TestWikiSyncPageMap:
    def test_every_documentation_page_is_published(self):
        workflow = (REPO_ROOT / ".github/workflows/wiki-sync.yml").read_text()
        mapped = set(re.findall(r'\["([^"]+\.md)"\]=', workflow))
        pages = {path.name for path in (REPO_ROOT / "documentation").glob("*.md")}
        assert pages == mapped
