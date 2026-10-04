#!/usr/bin/env python3
"""Keep the generated part of documentation/References.md in sync with the repo.

Reads dependencies and tooling from the files that declare them (backend/pyproject.toml,
frontend/package.json, backend/Dockerfile, .github/workflows/*.yml) and rewrites the block
between the BEGIN/END markers in References.md. Stdlib only, no network: links are built
deterministically from package names. The handwritten sections of the page are never touched.

Versions are deliberately left out: Dependabot bumps them weekly, and the block should only
change when a dependency is added or removed (the lockfiles already pin exact versions).

    python scripts/docs_references.py --write   # regenerate the block
    python scripts/docs_references.py --check   # exit 1 if the block is stale (used in CI)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

BEGIN = "<!-- BEGIN GENERATED: dependencies (edit via `task docs:references`, not by hand) -->"
END = "<!-- END GENERATED: dependencies -->"
REFERENCES_FILE = Path("documentation/References.md")

_REQ_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def python_packages(root: Path) -> list[tuple[str, str]]:
    """Direct Python dependencies as (name, group)."""
    pyproject = tomllib.loads((root / "backend/pyproject.toml").read_text())

    groups = {"runtime": pyproject["project"].get("dependencies", [])}
    for group, reqs in pyproject.get("dependency-groups", {}).items():
        groups[group] = reqs

    rows = []
    for group, reqs in groups.items():
        for req in reqs:
            match = _REQ_NAME.match(req)
            if match:
                rows.append((_normalize(match.group(1)), group))
    return sorted(rows)


def npm_packages(root: Path) -> list[tuple[str, str]]:
    """Direct npm dependencies as (name, group); empty until frontend/ exists."""
    package_json = root / "frontend/package.json"
    if not package_json.exists():
        return []
    data = json.loads(package_json.read_text())
    rows = []
    for key, group in (("dependencies", "runtime"), ("devDependencies", "dev")):
        rows.extend((name, group) for name in data.get(key, {}))
    return sorted(rows)


def _image_name(image: str) -> str:
    return re.split(r"[:@]", image, maxsplit=1)[0]


def _image_link(image: str) -> str:
    name = _image_name(image)
    if name.startswith("ghcr.io/"):
        owner_repo = "/".join(name.removeprefix("ghcr.io/").split("/")[:2])
        return f"https://github.com/{owner_repo}"
    if "/" in name:
        return f"https://hub.docker.com/r/{name}"
    return f"https://hub.docker.com/_/{name}"


def _dockerfile_text(root: Path) -> str:
    text = (root / "backend/Dockerfile").read_text()
    text = re.sub(r"\\\n", " ", text)
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def docker_images(root: Path) -> list[str]:
    text = _dockerfile_text(root)
    images = re.findall(r"^FROM\s+(?:--\S+\s+)*(\S+)", text, flags=re.MULTILINE)
    images += re.findall(r"^COPY\s+--from=(\S+)", text, flags=re.MULTILINE)
    return sorted({_image_name(image) for image in images if not image.startswith("$")})


def apt_packages(root: Path) -> list[str]:
    text = _dockerfile_text(root)
    packages = set()
    for match in re.finditer(r"apt-get install\s+([^&;\n]+)", text):
        packages.update(tok for tok in match.group(1).split() if not tok.startswith("-"))
    return sorted(packages)


def github_actions(root: Path) -> list[str]:
    """owner/repo of every third-party action used in the workflows."""
    repos = set()
    for workflow in sorted((root / ".github/workflows").glob("*.yml")):
        for ref in re.findall(r"uses:\s*([^\s@]+)@", workflow.read_text()):
            if not ref.startswith("./"):
                repos.add("/".join(ref.split("/")[:2]))
    return sorted(repos)


def render(root: Path) -> str:
    lines = [BEGIN, ""]

    lines += [
        "### Python packages",
        "",
        "Direct dependencies from `backend/pyproject.toml`. Exact versions are pinned in `backend/uv.lock`.",
        "",
        "| Package | Group | Link |",
        "|---|---|---|",
    ]
    for name, group in python_packages(root):
        lines.append(f"| `{name}` | {group} | [PyPI](https://pypi.org/project/{name}/) |")

    npm = npm_packages(root)
    if npm:
        lines += [
            "",
            "### npm packages",
            "",
            "Direct dependencies from `frontend/package.json`.",
            "",
            "| Package | Group | Link |",
            "|---|---|---|",
        ]
        for name, group in npm:
            lines.append(f"| `{name}` | {group} | [npm](https://www.npmjs.com/package/{name}) |")

    lines += [
        "",
        "### Container image",
        "",
        "From `backend/Dockerfile` (tags and digests are in the file).",
        "",
        "| Image | Link |",
        "|---|---|",
    ]
    for image in docker_images(root):
        lines.append(f"| `{image}` | [{_image_link(image).split('//', 1)[1]}]({_image_link(image)}) |")

    lines += ["", "| Debian package (`apt`) | Link |", "|---|---|"]
    for package in apt_packages(root):
        url = f"https://packages.debian.org/search?keywords={package}&searchon=names"
        lines.append(f"| `{package}` | [packages.debian.org]({url}) |")

    lines += [
        "",
        "### GitHub Actions",
        "",
        "Third-party actions used in `.github/workflows/`.",
        "",
        "| Action | Link |",
        "|---|---|",
    ]
    for repo in github_actions(root):
        lines.append(f"| `{repo}` | [GitHub](https://github.com/{repo}) |")

    lines += ["", END]
    return "\n".join(lines)


def apply_block(page: str, block: str) -> str:
    start, end = page.find(BEGIN), page.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError("References.md is missing the BEGIN/END GENERATED markers")
    return page[:start] + block + page[end + len(END) :]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite the generated block")
    mode.add_argument("--check", action="store_true", help="exit 1 if the generated block is stale")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)

    target = args.root / REFERENCES_FILE
    current = target.read_text()
    updated = apply_block(current, render(args.root))

    if args.check:
        if updated != current:
            print(
                f"{REFERENCES_FILE} is out of date with the dependencies. Run `task docs:references` and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{REFERENCES_FILE} is up to date.")
        return 0

    target.write_text(updated)
    print(f"Updated {REFERENCES_FILE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
