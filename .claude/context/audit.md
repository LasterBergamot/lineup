# Audit setup

Read by the `repo-audit` skill (from `ai-common`). The skill holds the procedure; this file
holds what this repo's audit covers, so each run is comparable with the Oct 2026 one that
produced epics #40–#46.

- **Repo and board:** `LasterBergamot/lineup`, project #4.
- **Marker line:** `_Found in the <Mon YYYY> repository audit._` Search for
  "Found in the Oct 2026 repository audit" to see what the last run filed.
- **Not covered here:** GDPR, the Hungarian rules and the OWASP baseline live in the
  `compliance-audit` skill. This audit reports security bugs it comes across but doesn't work
  through that checklist.

## Code explorer

Read in full (all under `backend/`): `app.py`, `main.py`, `lineup/**`, `alembic/env.py`,
`alembic/versions/*`, `tests/**`, `pyproject.toml`. Hunt for:
- validation mismatches between `lineup/api/models.py` and the saved-lineup schemas;
- ORM vs migration drift (nullable, ondelete, indexes, server defaults, constraints);
- async SQLAlchemy pitfalls (identity map, selectin, rollbacks);
- blocking calls inside `async def`; LibreOffice timeouts, concurrency and error mapping;
- owner/user filtering consistency, and fail-open behaviour when the id is `None`;
- header and filename injection; input limits; layering violations; dead code;
- tests that assert the wrong thing; the coverage config.

## Docs, infra and CI explorer

Read: `CLAUDE.md`, `.claude/**` (rules, context, skills, settings), `apm.yml`, `README.md`,
`documentation/*`, `Taskfile.yml`, `compose.yml`, `.gitignore`, `.github/**`,
`backend/Dockerfile`, `backend/.dockerignore`, `backend/.env.example`. Hunt for:
- docs that contradict each other or the code (verify structure trees with `ls`/`find`; task
  names vs the Taskfile; endpoints vs `backend/lineup/*/router.py`);
- roadmap items already done, or technically unworkable (e.g. RLS while the app connects as a
  role that bypasses RLS);
- Docker: root user, healthcheck, pinning, what `COPY . .` pulls in (the build context is
  `backend/`);
- CI: `permissions`, `concurrency`, SHA pinning, `--locked`, caching, whether migrations run;
- Dependabot ecosystems and groups; stale skill or command instructions; skills installed from
  `ai-common` that were edited in place (`apm audit` shows the drift).

## GitHub state explorer

Collect: issues with body, labels, milestone, assignee; parent/sub-issue and
`blockedBy`/`blocking` relations (GraphQL); project #4 items with Status/Area/Priority/Size;
labels, milestones, PRs with `closingIssuesReferences`; open Dependabot PRs and their checks;
open Dependabot alerts (`gh api repos/LasterBergamot/lineup/dependabot/alerts`); branch
protection and repo settings. Cross-reference with the roadmap docs and `git log`.

## Cheap reproductions

- A tiny ASGI request against in-memory SQLite (see `backend/tests/conftest.py`).
- `docker run --rm lineup ls -a /app` for what the image contains.
- Hotfix branches follow "Branches and environments" in `.claude/context/workflow.md`.
