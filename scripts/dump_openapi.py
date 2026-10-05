"""Print the backend's OpenAPI spec as JSON, without starting a server.

The frontend's typed API client (``frontend/src/api/schema.d.ts``) is generated from this spec.
Importing the FastAPI app and calling ``app.openapi()`` is enough; nothing connects to a
database. Run it with ``backend/`` as the working directory (``task fe:api`` does), because the
app's imports and resource paths are relative to it::

    cd backend && uv run python ../scripts/dump_openapi.py > ../frontend/src/api/openapi.json
"""

import json
import os
import sys

# Python puts this script's directory on sys.path, not the cwd, so `app` would not be found.
sys.path.insert(0, os.getcwd())

from app import app  # noqa: E402


def main() -> None:
    """Write the spec, with stable key order and a trailing newline, to stdout."""
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
