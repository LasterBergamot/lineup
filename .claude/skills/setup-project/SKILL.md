---
name: setup-project
description: Set up the lineup project from a fresh clone — install prerequisites, dependencies, build the container, run migrations, and verify everything works. Use when the repo has just been cloned and nothing is installed yet, or when helping someone get a working dev environment.
model: haiku
effort: high
---

Set up this repo as if it had just been cloned and nothing were installed. Do the steps below
**in order**. After each step, run its check and compare the result with "Expected". If a check
does not match, **stop**, tell the user which step failed with the exact command and its
output, and do not continue to the next step.

Ground rules:
- Treat `README.md` as the source of truth if anything here looks out of date; reread its
  "Prerequisites" and "Running" sections before you start.
- Never install system tools yourself and never use `sudo`: point the user to the link in the
  README "Prerequisites" section (installing is OS-dependent).
- Never read `backend/.env`, `backend/.env.migrate` or `frontend/.env`: they hold credentials.
- Python commands run with `backend/` as the working directory and frontend commands with
  `frontend/`. The `task` targets do that for you, so run them from the repo root.

## 1. Check the required tools

Run each command. Expected: every one prints a version.

```bash
python3 --version          # 3.13 or newer
uv --version
task --version
docker --version
docker compose version     # Compose 2.24 or newer
node --version            # only needed for the web app in frontend/
pnpm --version           # only needed for the web app in frontend/
```

Docker is required for PDF conversion (LibreOffice only runs inside the container). If a tool
is missing, give the user its link from the README and stop. `gh`, `yamllint`, `actionlint` and
`lazydocker` are optional: skip them unless the user asked about CI workflows or container
monitoring.

## 2. Install the backend dependencies

```bash
task install
```

Expected: it ends without errors and `backend/.venv` exists.

## 3. Local configuration (optional)

With no `backend/.env`, everything runs on a local SQLite file and nothing more is needed. Only
if the user wants Postgres/Supabase: copy `backend/.env.example` to `backend/.env` (it is
git-ignored) and tell the user to fill it in themselves. `task db:status` shows which database
`backend/.env` selects.

## 4. Run the backend tests

```bash
task test
```

Expected: all tests pass and the run reports `Required test coverage of 100.0% reached`. If it
does not, the environment is wrong, not the code (wrong Python version, stale lock file):
stop and report.

## 5. Build and start the container

```bash
task build
task up
```

`task build` builds the `lineup` image from `backend/` (LibreOffice and the fonts are baked
in). `task up` starts it through `compose.yml`.

Check (it may take up to 30 seconds after `task up`; retry a few times):

```bash
curl -sf http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`. The API docs are at `http://127.0.0.1:8000/docs`.

## 6. Migrations

Skip this step unless the user wants a local SQLite file migrated. The container creates its
own tables when it starts, inside the container, so it does not need this.

```bash
task migrate
```

This applies the Alembic migrations to the **host's** `backend/lineup.db` (the default
`DATABASE_URL`); it does not touch the container's database. Expected: it ends without errors.

## 7. End-to-end PDF check (recommended)

`task test-e2e` builds the image again, starts its **own** container, runs the real
PDF-conversion fidelity test and then **stops the container**, including the one from step 5.
Tell the user before running it.

```bash
task test-e2e
```

Expected: the tests pass. Afterwards run `task up` again if the user wants the API running.

## 8. Frontend (optional)

Only if the user works on the web app and step 1 showed `node` and `pnpm`:

```bash
task fe:install
task fe:check
```

Expected: both end without errors. `task fe:dev` starts the dev server on `http://localhost:5173`
and proxies `/api` to the container from step 5, so keep that running.

## 9. Report

Write a short summary with three lists: what is installed, what is running, and what failed or
was skipped (for example Docker unavailable or a test failure). Do not say the setup succeeded
unless every checked step matched "Expected".
