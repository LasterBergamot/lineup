# Lineup — Claude Code Project Context

This file is a **router**: it holds only what every session needs. The detail for an area lives in
`.claude/rules/` (loads by itself when you read or edit a matching file) and `.claude/context/`
(read it when the table below says so). Read the file for your task before you start.

## What this is

Water polo lineup document generator. Takes match details and player info, fills a `.docx` template (`backend/resources/rajtlista.docx`), and returns the result via a REST API as a PDF (default) or DOCX. PDF conversion uses LibreOffice headless, which only exists inside the container, so run the API with `task build` + `task up`, not `task serve`. A persistence layer (teams, players, saved lineups; SQLAlchemy async + Alembic) runs on SQLite locally and on Postgres (Supabase) via `DATABASE_URL`; every data route needs a signed-in user.

**Repo layout**: the Python backend lives in `backend/` and the Vite/React web app lives in `frontend/`; the repo root only holds what is shared or cross-cutting — `Taskfile.yml`, `compose.yml`, `.github/`, `.claude/`, `documentation/`, `README.md`, `CLAUDE.md`, `PLAN.md`. **Every Python command must run with `backend/` as its working directory**, because `alembic.ini` (`prepend_sys_path = .`), the `resources/…` template paths, pytest's rootdir (`from app import app`), `--cov=lineup` and the `./lineup.db` SQLite default are all cwd-relative. The root `Taskfile.yml` sets `dir: backend` on those tasks, so use `task …` from anywhere; if you run `uv`/`pytest`/`alembic` by hand, `cd backend` first. **Every frontend command runs with `frontend/` as its working directory** (the `task fe:*` targets set `dir: frontend`). The file tree is in `README.md` ("Project structure").

## Router: working on X → read Y

| Working on | Read |
|------------|------|
| Backend API, auth, modules, OpenAPI conventions | `.claude/rules/backend-api.md` (loads for `backend/lineup/**`, `backend/app.py`) |
| Data model, migrations, engine, Postgres/Supabase | `.claude/rules/backend-db.md` (loads for `backend/lineup/db/**`, `backend/alembic/**`) |
| Backend tests | `.claude/rules/backend-tests.md` (loads for `backend/tests/**`) |
| Lint config, ruff `S` ignores | `.claude/rules/backend-security.md` |
| Dockerfile, fonts, Compose | `.claude/rules/container.md` |
| Frontend | `.claude/rules/frontend.md` (loads for `frontend/**`) |
| Writing docs or wiki pages | `.claude/rules/documentation.md` (loads for `documentation/**`, `README.md`) |
| Adding a field, a log line, a stored file, a browser-storage key or a third-party service (personal data) | `documentation/Privacy-and-Security.md` (the data inventory; update it in the same PR) |
| Setting up a dev machine | `documentation/Setup.md` (the `setup-project` skill follows it) |
| Tasks, environment variables, branches, merge rules | `.claude/context/workflow.md` |
| Opening a PR, Dependabot alerts and PRs | `.claude/context/pr-checklist.md` |
| Filing or editing issues (labels, milestones, epics, board) | `.claude/context/issues.md` |
| Which docs exist and how they are published | `.claude/context/docs.md` |
| Auditing the repo | `.claude/context/audit.md` |
| Skills, settings, APM, how this context is organised | `.claude/context/claude-code.md` |
| The dev-preview work (frontend, auth, invitations, dev deploy) | `PLAN.md` |
| Newcomer overview, design rationale, roadmaps | `documentation/Newcomer-Guide.md`, `documentation/Current-State-Backend.md`, `documentation/Roadmap-Backend.md` |

Explore and Plan subagents load neither this file nor the rules: put the rule file's path in their prompt.

## Always-on rules

- `PLAN.md` is the working plan for the dev preview. Read it when picking up that work; tick its checklist and add a progress-log row (with the real PR number) when an item lands; delete the file once the whole plan is done.
- On **every** change, check `README.md`, the rule/context file for the area you touched (`.claude/context/claude-code.md` has the map) and the matching `documentation/` page(s), and update whatever the change makes stale (API, tasks, prerequisites, structure, workflow, dependencies, container, CI). A PR must contain a docs diff, or an explicit `No doc impact: <reason>` line in its description plus the `no-docs` label. CI enforces this (`.github/workflows/docs-check.yml`, `scripts/check_docs_touched.sh`); the `create-pr` skill runs `update-documentation` as a gate.
- `documentation/` is mirrored into the GitHub wiki by CI, so it must stay current the same way `README.md` does. Keep `documentation/Newcomer-Guide.md` and `documentation/References.md` current too; the details are in `.claude/rules/documentation.md`.
- **Docstrings are documentation too.** Every new or changed public module, class, function and method in `backend/lineup/`, `app.py` and `main.py` needs a docstring that says what it is *for*, the non-obvious *why* (constraint, invariant, gotcha) and what it raises or returns when the signature doesn't show it, not a restatement of the name. Audience: a junior developer new to the repo. Pydantic models and FastAPI route functions are shown in `/docs`, so write those for an API consumer. `task lint` enforces presence (ruff `D1`; tests and migration revisions are exempt); the content is on you, and `update-documentation` checks it.
- For any new code: write tests. For changed code: update existing tests. Coverage must stay at 100%.
- When starting implementation of a feature or fix, run the `compliance-audit` skill in quick mode (`compliance-audit quick <issue#>`) before coding, and fold its findings into the plan and the tests. It checks the change against the GDPR/security requirements in `.claude/skills/compliance-audit/requirements.md` (epic #92) and stops immediately when nothing is compliance-relevant.
- The generic skills and the `convention-reviewer` agent are installed from `ai-common` (pinned in `apm.yml`, listed in `apm.lock.yaml`). Never edit them here: change lineup's values in `.claude/context/`, or change the skill in `ai-common` and bump the tag (`.claude/context/claude-code.md`).
- Before creating a PR, follow `.claude/context/pr-checklist.md` (Dependabot alerts and version-update PRs).
- Never edit generated files (`frontend/src/api/openapi.json`, `schema.d.ts`, the generated block in `documentation/References.md`); regenerate them with the `task` targets named in the rule files.
