# Setup

The step-by-step way to go from a fresh clone to a working dev environment. It is written for a
person at a terminal **and** for an AI agent (Claude Code, Copilot, Cursor, Codex…): every step
has a command, the result to expect, and what to do when the result is different. The
`setup-project` Claude Code skill only follows this page, so this page is the one to keep
current.

Work through the steps **in order**. After each step, compare the output with **Expected**. If it
doesn't match, stop there: fix that step before going on, because the later steps assume the
earlier ones worked.

## Ground rules (read these first if you are an agent)

- Never install system tools yourself and never use `sudo`. Installing is OS-specific: point the
  person to the links in the README's *Prerequisites* section and stop.
- Never read `backend/.env`, `backend/.env.migrate` or `frontend/.env`. They hold credentials.
- Run the commands from the repo root. The `task` targets switch to `backend/` or `frontend/`
  themselves; if you run `uv`, `pytest` or `alembic` by hand, `cd backend` first.
- Tell the person before a step that stops a running container (step 7).
- At the end, report what is installed, what is running, and what failed or was skipped. Don't
  call the setup a success unless every step you ran matched **Expected**.

## 1. Check the tools

```bash
task doctor
```

`task doctor` runs `scripts/doctor.sh`. It checks the required tools and their minimum versions
(Python 3.13+, uv, Task, Docker, Docker Compose 2.24+, Node.js, pnpm, gh) and lists the optional
ones (yamllint, actionlint, lazydocker).

**Expected:** every required line starts with `ok`, and the last line is
`All required tools are present.`

**If not:** install what is marked `FAIL` from the README's *Prerequisites* section, then run it
again. `skip` lines are optional tools. Node.js and pnpm are required because the web app in
`frontend/` and the `task fe:*` checks need them; pnpm's version is pinned by `packageManager`
in `frontend/package.json`, so a newer pnpm switches to it by itself. `gh` is required because
issues, pull requests and CI checks are all handled through it; run `gh auth login` once (an
agent must not do that for you).

If `task` itself is "command not found": Task is missing, or (on Arch Linux) it is installed as
`go-task`. Then run `bash scripts/doctor.sh` directly, and add `alias task=go-task` to your shell
config.

## 2. Install the backend dependencies

```bash
task install
```

This runs `uv sync` in `backend/`, which creates `backend/.venv` with the exact versions from
`backend/uv.lock`.

**Expected:** it ends without errors and `backend/.venv` exists.

## 3. Local configuration (optional)

With no `backend/.env`, everything runs on a local SQLite file (`backend/lineup.db`) and nothing
more is needed. Skip this step unless you want the hosted Postgres (Supabase).

For Postgres: copy `backend/.env.example` to `backend/.env` (it is git-ignored) and fill it in
yourself; the values are explained in the file and in the README's *Using the Supabase dev database* section. Then
`task db:postgres` switches to it and `task db:status` shows which database is active.

**Expected:** `task db:status` names the database you meant to use.

## 4. Run the backend tests

```bash
task test
```

**Expected:** all tests pass, and the run ends with `Required test coverage of 100.0% reached`.

**If not:** on a fresh clone this means the environment is wrong, not the code. Usual causes are
an old Python or a stale `backend/.venv` (delete it and repeat step 2).

## 5. Build and start the container

```bash
task build
task up
```

`task build` builds the `lineup` image from `backend/` (LibreOffice and the fonts are inside it;
PDF conversion only works in the container). `task up` starts it with `compose.yml`.

Check that the API answers. It can take up to 30 seconds after `task up`, so retry a few times:

```bash
curl -sf http://127.0.0.1:8000/health
```

**Expected:** `{"status":"ok"}`. The interactive API docs are at `http://127.0.0.1:8000/docs`
(they are off when `ENV=production` or `DOCS_ENABLED=false`; `/health` is always there).

## 6. Migrations (usually skip)

The container creates its own tables when it starts, so it does not need this step. Run it only
if you want the host's SQLite file (`backend/lineup.db`) migrated, for example to use `task serve`.

```bash
task migrate
```

**Expected:** it ends without errors. It does not touch the container's database.

## 7. End-to-end PDF check (recommended)

This proves the real PDF conversion matches the reference layout. It builds the image again,
makes a throw-away signing key in `.e2e-auth/`, starts its **own** container as a separate Compose
project (`lineup-e2e`, host port 8001, no `backend/.env`, its own data volume), runs the tests, and then
removes that container and volume. The container from step 5 keeps running.

```bash
task test-e2e
```

**Expected:** the tests pass, and `http://127.0.0.1:8000/health` still answers.

## 8. Frontend

Step 1 showed Node.js and pnpm as `ok`, so the web app can be installed and checked:

```bash
task fe:install
task fe:check
```

**Expected:** both end without errors. `task fe:dev` then starts the web app on
`http://localhost:5173`; it forwards `/api` to the container from step 5, so keep that running.

## 9. Done: what next

- [[Newcomer Guide]]: what each part does and how to make a first change.
- The README's *Available tasks* table: every `task` target.
- [[Auth Setup]]: only needed if you sign in against a real Supabase project.
