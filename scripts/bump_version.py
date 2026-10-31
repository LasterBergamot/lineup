#!/usr/bin/env python3
"""Bump the repo-wide version in `backend/pyproject.toml` and `frontend/package.json` (#17).

Usage: bump_version.py patch|minor|major|X.Y.Z    (or --show to print the current version)

One SemVer version covers backend and frontend. This only edits the two files; the change goes
through a normal PR, and the manual `release` workflow then tags the merged commit. `task
release:bump` runs this and regenerates the API client, because the OpenAPI spec embeds the
backend version.
"""

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "backend" / "pyproject.toml"
PACKAGE_JSON = ROOT / "frontend" / "package.json"

SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
# Only the top-level version: `[project]` is the first table, and in package.json the
# first `"version"` key is the package's own.
PYPROJECT_VERSION = re.compile(r'^version = "[^"]*"$', re.MULTILINE)
PACKAGE_VERSION = re.compile(r'^(\s*"version": )"[^"]*"', re.MULTILINE)


def parse(version: str) -> tuple[int, int, int]:
    """Split `MAJOR.MINOR.PATCH`; raises `ValueError` for anything else (no pre-release tags)."""
    if not SEMVER.fullmatch(version):
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    major, minor, patch = (int(part) for part in version.split("."))
    return major, minor, patch


def next_version(current: str, change: str) -> str:
    """Return the version after `current`: `change` is patch, minor, major or an explicit version."""
    major, minor, patch = parse(current)
    if change == "major":
        return f"{major + 1}.0.0"
    if change == "minor":
        return f"{major}.{minor + 1}.0"
    if change == "patch":
        return f"{major}.{minor}.{patch + 1}"
    parse(change)
    return change


def read_versions() -> tuple[str, str]:
    """Return `(backend, frontend)` as currently committed."""
    backend = tomllib.loads(PYPROJECT.read_text())["project"]["version"]
    frontend = json.loads(PACKAGE_JSON.read_text())["version"]
    return backend, frontend


def write_versions(version: str) -> None:
    """Rewrite both files in place, touching nothing but the version string."""
    pyproject, count = PYPROJECT_VERSION.subn(f'version = "{version}"', PYPROJECT.read_text(), 1)
    if count != 1:
        raise ValueError(f"no version line found in {PYPROJECT}")
    package, count = PACKAGE_VERSION.subn(rf'\1"{version}"', PACKAGE_JSON.read_text(), 1)
    if count != 1:
        raise ValueError(f"no version key found in {PACKAGE_JSON}")
    PYPROJECT.write_text(pyproject)
    PACKAGE_JSON.write_text(package)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("change", nargs="?", help="patch, minor, major or an explicit X.Y.Z")
    parser.add_argument("--show", action="store_true", help="print the current version")
    args = parser.parse_args(argv)

    backend, frontend = read_versions()
    if backend != frontend:
        print(f"backend ({backend}) and frontend ({frontend}) versions differ", file=sys.stderr)
        return 1
    if args.show or not args.change:
        print(backend)
        return 0
    try:
        new = next_version(backend, args.change)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    if new == backend:
        print(f"already at {backend}", file=sys.stderr)
        return 2
    write_versions(new)
    print(f"{backend} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
