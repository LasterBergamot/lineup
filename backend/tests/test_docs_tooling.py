"""Tests for the repo-level docs tooling in ../scripts and the wiki-sync page map."""

import glob
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
COPY --from=base /a /a
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

    def test_docker_images_drop_tags_digests_comments_build_args_and_stage_names(
        self, fake_root
    ):
        (fake_root / "backend/Dockerfile").write_text(
            DOCKERFILE + "FROM debian@sha256:abc\n"
        )
        assert refs.docker_images(fake_root) == [
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
        check=False,
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
        "docs_file",
        [
            "README.md",
            "CLAUDE.md",
            "documentation__Home.md",
            ".claude__rules__backend-api.md",
            ".claude__context__workflow.md",
        ],
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


def _load_sync_wiki():
    spec = importlib.util.spec_from_file_location("sync_wiki", SCRIPTS / "sync_wiki.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_wiki = _load_sync_wiki()
DOCS = REPO_ROOT / "documentation"


class TestWikiPageNames:
    """The wiki page for a documentation file is named after its H1 (#63)."""

    def test_every_documentation_page_gets_a_unique_name(self):
        pages = sync_wiki.page_map(DOCS)
        assert {p.name for p in pages} == {p.name for p in DOCS.glob("*.md")}
        assert len(set(pages.values())) == len(pages)

    def test_home_stays_home_and_titles_become_hyphenated_names(self):
        pages = {p.name: n for p, n in sync_wiki.page_map(DOCS).items()}
        assert pages["Home.md"] == "Home.md"
        assert pages["Current-State-Backend.md"] == "Current-State:-Backend.md"
        assert pages["Privacy-and-Security.md"] == "Privacy-and-Security.md"

    def test_every_page_is_linked_from_home(self):
        """A page nobody links to is published but unreachable."""
        home = (DOCS / "Home.md").read_text()
        for source in DOCS.glob("*.md"):
            if source.name == "Home.md":
                continue
            title = sync_wiki.wiki_name(source).removesuffix(".md").replace("-", " ")
            assert f"[[{title}]]" in home, f"{source.name} is not linked from Home.md"

    def test_a_page_without_a_title_is_an_error(self, tmp_path):
        (tmp_path / "Untitled.md").write_text("just text\n")
        with pytest.raises(ValueError, match="no '# Title'"):
            sync_wiki.page_map(tmp_path)

    def test_two_pages_with_the_same_title_are_an_error(self, tmp_path):
        (tmp_path / "A.md").write_text("# Same\n")
        (tmp_path / "B.md").write_text("# Same\n")
        with pytest.raises(ValueError, match="would both become"):
            sync_wiki.page_map(tmp_path)


class TestWikiSync:
    @pytest.fixture
    def folders(self, tmp_path):
        docs, wiki = tmp_path / "documentation", tmp_path / "wiki"
        docs.mkdir()
        wiki.mkdir()
        (docs / "Home.md").write_text("# Welcome\n")
        (docs / "Some-Page.md").write_text("# Some Page\nbody\n")
        return docs, wiki

    def test_copies_pages_under_their_wiki_names(self, folders):
        docs, wiki = folders
        written, deleted = sync_wiki.sync(docs, wiki)
        assert sorted(written) == ["Home.md", "Some-Page.md"]
        assert deleted == []
        assert (wiki / "Some-Page.md").read_text() == "# Some Page\nbody\n"

    def test_a_new_page_needs_no_other_edit(self, folders):
        docs, wiki = folders
        (docs / "Brand-New.md").write_text("# Brand New Thing\n")
        sync_wiki.sync(docs, wiki)
        assert (wiki / "Brand-New-Thing.md").exists()

    def test_deletes_pages_whose_source_is_gone_but_keeps_wiki_chrome(self, folders):
        docs, wiki = folders
        (wiki / "Old-Page.md").write_text("stale")
        (wiki / "_Sidebar.md").write_text("mine")
        (wiki / "image.png").write_bytes(b"x")
        _, deleted = sync_wiki.sync(docs, wiki)
        assert deleted == ["Old-Page.md"]
        assert (wiki / "_Sidebar.md").exists()
        assert (wiki / "image.png").exists()

    def test_a_rename_replaces_the_old_page(self, folders):
        docs, wiki = folders
        sync_wiki.sync(docs, wiki)
        (docs / "Some-Page.md").write_text("# Renamed Page\n")
        sync_wiki.sync(docs, wiki)
        assert not (wiki / "Some-Page.md").exists()
        assert (wiki / "Renamed-Page.md").exists()

    def test_main_mirrors_and_reports(self, folders, capsys):
        docs, wiki = folders
        (wiki / "Old.md").write_text("stale")
        assert sync_wiki.main([str(docs), str(wiki)]) == 0
        out = capsys.readouterr().out
        assert "Wrote 2 wiki pages." in out
        assert "Deleted Old.md" in out

    def test_main_lists_the_mapping_without_a_wiki_folder(self, folders, capsys):
        docs, _ = folders
        assert sync_wiki.main([str(docs), "--list"]) == 0
        assert "Some-Page.md -> Some-Page.md" in capsys.readouterr().out

    def test_main_needs_a_wiki_folder_unless_listing(self, folders):
        docs, _ = folders
        with pytest.raises(SystemExit):
            sync_wiki.main([str(docs)])

    def test_main_fails_with_a_workflow_error_on_a_bad_page(self, folders, capsys):
        docs, wiki = folders
        (docs / "Bad.md").write_text("no heading")
        assert sync_wiki.main([str(docs), str(wiki)]) == 1
        assert "::error::" in capsys.readouterr().err


class TestWikiSyncWorkflow:
    @pytest.fixture
    def workflow(self):
        return (REPO_ROOT / ".github/workflows/wiki-sync.yml").read_text()

    def test_has_no_hand_kept_page_map(self, workflow):
        assert "PAGE_MAP" not in workflow
        assert "python3 scripts/sync_wiki.py documentation wiki" in workflow

    def test_reruns_when_the_workflow_or_script_changes_and_can_be_started_by_hand(
        self, workflow
    ):
        assert '- ".github/workflows/wiki-sync.yml"' in workflow
        assert '- "scripts/sync_wiki.py"' in workflow
        assert "workflow_dispatch:" in workflow

    def test_runs_queue_instead_of_racing_and_only_publish_develop(self, workflow):
        assert "group: wiki-sync" in workflow
        assert "cancel-in-progress: false" in workflow
        assert "if: github.ref == 'refs/heads/develop'" in workflow


CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
RULES_DIR = REPO_ROOT / ".claude" / "rules"
MAX_ROUTER_LINES = 100


def _rule_globs(rule: Path) -> list[str] | None:
    """Return the `paths:` globs from a rule file's frontmatter, or None if it has none."""
    match = re.match(r"---\n(.*?)\n---\n", rule.read_text(), re.DOTALL)
    if match is None or "paths:" not in match.group(1):
        return None
    return re.findall(r'^\s*-\s*"([^"]+)"\s*$', match.group(1), re.MULTILINE)


class TestClaudeContextRouter:
    """`CLAUDE.md` is a router: it stays small and every rule and target it names is real."""

    def test_router_stays_small(self):
        lines = CLAUDE_MD.read_text().count("\n")
        assert lines <= MAX_ROUTER_LINES, (
            f"CLAUDE.md has {lines} lines (max {MAX_ROUTER_LINES}). Move detail into "
            ".claude/rules/ (path-scoped) or .claude/context/ so every session isn't loading it."
        )

    def test_every_path_the_router_names_exists(self):
        tokens = re.findall(r"`([^`\s]+)`", CLAUDE_MD.read_text())
        paths = {
            token
            for token in tokens
            if re.fullmatch(r"[\w./-]+", token)
            and ("/" in token or token.endswith(".md"))
            and not token.startswith(("./", "/"))
        }
        missing = sorted(path for path in paths if not (REPO_ROOT / path).exists())
        assert not missing, f"CLAUDE.md names paths that don't exist: {missing}"

    def test_every_rule_is_path_scoped(self):
        """A rule without `paths:` loads at session start, which defeats the router."""
        rules = sorted(RULES_DIR.glob("*.md"))
        assert rules, "expected rule files in .claude/rules/"
        unscoped = [rule.name for rule in rules if not _rule_globs(rule)]
        assert not unscoped, f"rules without `paths:` frontmatter: {unscoped}"

    @pytest.mark.parametrize(
        "rule", sorted(RULES_DIR.glob("*.md")), ids=lambda p: p.name
    )
    def test_every_glob_matches_a_file(self, rule):
        for pattern in _rule_globs(rule) or []:
            hits = glob.glob(
                pattern, root_dir=REPO_ROOT, recursive=True, include_hidden=True
            )
            assert hits, f"{rule.name}: glob {pattern!r} matches nothing"

    def test_every_rule_is_named_in_the_router(self):
        router = CLAUDE_MD.read_text()
        unlisted = [
            rule.name
            for rule in RULES_DIR.glob("*.md")
            if f".claude/rules/{rule.name}" not in router
        ]
        assert not unlisted, (
            f"rules missing from the CLAUDE.md router table: {unlisted}"
        )


SKILL_FILES = sorted((REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md"))
AGENT_FILES = sorted((REPO_ROOT / ".claude" / "agents").glob("*.md"))
MODEL_ALIASES = {"opus", "sonnet", "haiku", "inherit"}
EFFORT_LEVELS = {"low", "medium", "high", "xhigh", "max"}


def _frontmatter_value(path: Path, key: str) -> str | None:
    """Return a top-level frontmatter value of a skill or agent file, or None if absent."""
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
    assert match, f"{path} has no frontmatter"
    found = re.search(rf"^{key}:\s*(\S+)\s*$", match.group(1), re.MULTILINE)
    return found.group(1) if found else None


class TestSkillModelAliases:
    """Skills and agents pin a model *alias*, so they follow the newest model of a tier."""

    def test_skills_were_found(self):
        assert SKILL_FILES, "expected skills in .claude/skills/"

    @pytest.mark.parametrize(
        "path", SKILL_FILES + AGENT_FILES, ids=lambda p: p.parent.name or p.stem
    )
    def test_model_is_an_alias_never_a_full_id(self, path):
        model = _frontmatter_value(path, "model")
        assert model is None or model in MODEL_ALIASES, (
            f"{path.relative_to(REPO_ROOT)}: model {model!r} is not one of {sorted(MODEL_ALIASES)}. "
            "Use an alias: it resolves to the newest model of that tier, while a full ID "
            "such as claude-sonnet-5-5 goes stale at the next release."
        )

    @pytest.mark.parametrize(
        "path", SKILL_FILES + AGENT_FILES, ids=lambda p: p.parent.name or p.stem
    )
    def test_effort_is_a_valid_level(self, path):
        effort = _frontmatter_value(path, "effort")
        assert effort is None or effort in EFFORT_LEVELS, (
            f"{path.relative_to(REPO_ROOT)}: effort {effort!r} is not one of {sorted(EFFORT_LEVELS)}"
        )


APM_LOCK = REPO_ROOT / "apm.lock.yaml"


class TestAiCommonSkills:
    """The generic skills come from `ai-common` (APM, `apm.yml`) and read lineup's context files."""

    def test_every_context_file_a_skill_reads_exists(self):
        """A generic skill holds the procedure; lineup's values live in `.claude/context/*.md`."""
        named = {
            name
            for path in SKILL_FILES + AGENT_FILES
            for name in re.findall(r"\.claude/context/([\w-]+\.md)", path.read_text())
        }
        assert named, "expected skills to name .claude/context/ files"
        missing = sorted(
            name
            for name in named
            if not (REPO_ROOT / ".claude" / "context" / name).exists()
        )
        assert not missing, f"skills read context files that don't exist: {missing}"

    def test_deployed_files_are_committed(self):
        """Deployed skills are committed so contributors and CI don't need the private repo."""
        deployed = re.findall(
            r"^  - (\.claude/\S+)$", APM_LOCK.read_text(), re.MULTILINE
        )
        assert deployed, "expected deployed files in apm.lock.yaml"
        missing = sorted(path for path in deployed if not (REPO_ROOT / path).exists())
        assert not missing, (
            f"apm.lock.yaml lists files that aren't in the repo: {missing}. Run `apm install`."
        )
