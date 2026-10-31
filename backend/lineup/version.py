"""The app version, read from `pyproject.toml` so that file stays its single source (#17)."""

import tomllib
from pathlib import Path

# Anchored to this file, like the template path, so it works wherever the process starts.
PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def read_version() -> str:
    """Return `[project].version` from `backend/pyproject.toml`.

    The project is not installed as a package (there is no build backend), so
    `importlib.metadata` cannot see it. The Dockerfile copies `pyproject.toml` next to the
    code for the same reason, so this works inside the image too.
    """
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


APP_VERSION = read_version()
