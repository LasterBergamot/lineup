# Lineup — Claude Code Project Context

## Instructions

- Read this file at the start of every session before doing anything.
- `PLAN.md` is the working plan for the dev preview (frontend, auth, invitations, dev deployment). Read it when picking up that work; tick its checklist and add a progress-log row (with the real PR number) when an item lands; delete the file once the whole plan is done.
- After completing any task: update this file if architecture, conventions, tasks, or modules changed.
- On **every** change, check `README.md`, `CLAUDE.md` and the matching `documentation/` page(s) and update whatever the change makes stale (API, tasks, prerequisites, structure, workflow, dependencies, container, CI). A PR must contain a docs diff, or an explicit `No doc impact: <reason>` line in its description plus the `no-docs` label. CI enforces this (`.github/workflows/docs-check.yml`, `scripts/check_docs_touched.sh`); the `create-pr` skill runs `update-documentation` as a gate.
- **Docstrings are documentation too.** Every new or changed public module, class, function and method in `backend/lineup/`, `app.py` and `main.py` needs a docstring that says what it is *for*, the non-obvious *why* (constraint, invariant, gotcha) and what it raises or returns when the signature doesn't show it, not a restatement of the name. Audience: a junior developer new to the repo. Pydantic models and FastAPI route functions are shown in `/docs`, so write those for an API consumer. `task lint` enforces presence (ruff `D1`; tests and migration revisions are exempt); the content is on you, and `update-documentation` checks it.
- After any change that affects current-state or roadmap facts (architecture, API surface, data model, dev workflow, planned work): update the relevant file(s) under `documentation/` to match — it's mirrored into the GitHub wiki by CI, so it needs to stay current the same way `README.md` does.
- When starting implementation of a feature or fix, run the `compliance-audit` skill in quick mode (`compliance-audit quick <issue#>`) before coding, and fold its findings into the plan and the tests. It checks the change against the GDPR/security requirements in `.claude/skills/compliance-audit/requirements.md` (epic #92) and stops immediately when nothing is compliance-relevant.
- For any new code: write tests. For changed code: update existing tests. Coverage must stay at 100%.
- `documentation/Newcomer-Guide.md` (wiki: *Newcomer Guide*) is the junior-developer walkthrough: tools and why we use them, glossary, one request through the layers, how to run, test and make a first change. Keep it current when the architecture, the request flow, the tooling or the contribution workflow changes.
- `documentation/References.md` (wiki: *References*) lists the official docs for every library, tool, service, spec and regulation we use. Its *Libraries, images and actions* block is generated: after changing a dependency, `Dockerfile` or workflow run `task docs:references` (CI's `task docs:check` fails on a stale block). Add a row to the handwritten tables when you adopt a new service, tool, spec or regulation.
- Every new file in `documentation/` must also be added to `PAGE_MAP` in `.github/workflows/wiki-sync.yml` (a test and the workflow fail otherwise) and linked from `documentation/Home.md`.
- Write `README.md` and `documentation/` so a newcomer with no prior context can understand the architecture, the codebase, and how a request flows through it — explain the "why", not just record what changed. Keep that bar on every doc update.
- Before creating a PR in this repo, check for open GitHub Dependabot alerts via `gh api repos/LasterBergamot/lineup/dependabot/alerts` (filter for `"state": "open"`) and surface any findings to the user.
- Also check the open Dependabot version-update PRs (`gh pr list --state open --author "app/dependabot"`, then `gh pr checks <n>` / `gh pr view <n>` for each). Alerts and these PRs are separate: an empty alerts list says nothing about pending PRs. A PR is **blocking** if its CI checks fail, it has merge conflicts, or it is a major-version bump (or touches a core dependency such as SQLAlchemy, FastAPI or asyncpg) whose effect on the current branch's code can't be shown to be safe; otherwise it is **non-blocking**.
  - Non-blocking PRs: list them for the user, and once the user confirms (merging is a state-changing `gh` command, so the usual confirmation rule still applies), merge them, then bring the current branch up to date with the updated `develop` (merge `develop` into it, resolving `backend/pyproject.toml`/`backend/uv.lock` conflicts), run `uv sync` (in `backend/`), and re-run `task lint` and `task test` before creating the PR.
  - Blocking PRs: don't merge them. Report each with the reason (failing check, conflict, breaking change) and discuss the next step with the user.

---

## Project Overview

Water polo lineup document generator. Takes match details and player info, fills a `.docx` template (`backend/resources/rajtlista.docx`), and returns the result via a REST API as either a PDF (default) or DOCX.

PDF conversion uses LibreOffice headless, which is only available inside the container — the API must be run via `task build` + `task up`, not `task serve`.

**Repo layout**: the Python backend lives in `backend/` (and a Vite/React app will live in `frontend/`); the repo root only holds what is shared or cross-cutting — `Taskfile.yml`, `compose.yml`, `.github/`, `.claude/`, `documentation/`, `README.md`, `CLAUDE.md`, `PLAN.md`. **Every Python command must run with `backend/` as its working directory**, because `alembic.ini` (`prepend_sys_path = .`), the `resources/…` template paths, pytest's rootdir (`from app import app`), `--cov=lineup` and the `./lineup.db` SQLite default are all cwd-relative. The root `Taskfile.yml` sets `dir: backend` on those tasks, so use `task …` from anywhere; if you run `uv`/`pytest`/`alembic` by hand, `cd backend` first. The split exists so CI, Docker and Dependabot can treat the two sides separately (the Docker build context is `backend/`, so repo-root files never enter the image).

The template is authored in Calibri/Calibri Light (proprietary). The container ships the libre metric-compatible substitutes (Carlito etc.) so the PDF layout matches the source `.docx`; without them LibreOffice substitutes a differently-sized font and the tab-stop/table layout drifts.

There's also a persistence layer (Teams, Players, Saved Lineups) backed by SQLAlchemy async ORM + Alembic, running on in-memory/file SQLite locally and swappable to Postgres (Supabase) via `DATABASE_URL`. It's pre-Auth: `user_id`/`owner_id` columns exist everywhere but always resolve to `None` until real auth is wired in. See `documentation/Current-State-Backend.md` for the design rationale (snapshot vs. soft-reference strategy, ERD) and `documentation/Roadmap-Backend.md` for the Supabase/OAuth roadmap.

---

## Architecture

### API

- `GET /health[?db=1]` — liveness / readiness probe; `200 {"status":"ok"}` or `503 {"status":"unavailable"}`
- `POST /lineups?format=pdf|docx` — fills the template, converts to PDF (or returns DOCX), streams the file back
- `format` query param defaults to `pdf`; `docx` skips LibreOffice conversion entirely
- Request body: `LineupRequest` (match, division, team_name, cap, date, coach, doctor, assistant_coach, team_leader, ball_thrower, players)
- `cap` must be `"Fehér"` or `"Kék"`; players: 1–15, unique cap numbers 1–15
- Returns binary file with `Content-Disposition: attachment` header (`filename=` ASCII fallback + `filename*=UTF-8''…`)
- Errors: 422 invalid input, 503 (+ `Retry-After`) when all PDF conversion slots are busy, 504 LibreOffice timeout, 500 other rendering failures — shared with `POST /lineups/saved/{id}/generate` via `lineup/api/file_response.py`

#### Teams / Players / Saved Lineups

- `GET/POST /teams`, `GET/PUT/DELETE /teams/{id}` — CRUD, paginated list (`?limit=&offset=`, `limit` 1–200, default 20; no "all" mode)
- `GET /teams/pool?search=&limit=` — shared opponent pool: public teams (`is_public=True`) only, plain list (not the paginated envelope), `limit` 1–100, `search` is a literal substring (`icontains(..., autoescape=True)`, max 120 chars). Registered **before** `/teams/{id}` in the router so `"pool"` doesn't get swallowed as a `team_id` path param.
- `DELETE /teams/{id}` returns **409** if the team still has roster players assigned (`Player.team_id`); otherwise 200. This check is app-level, not DB-level.
- `GET/POST /players`, `GET/PUT/DELETE /players/{id}` — CRUD; `team_id` is optional on create/update and filterable on list; an unknown `team_id` → **404** `Team not found` (checked in `players/service.py`, ownership-aware via `team_repo.get_team`). `DELETE /players/{id}` is **unconditionally** safe (204) — it never blocks, because saved lineups store frozen snapshots, not live references.
- `GET/POST /lineups/saved`, `GET/DELETE /lineups/saved/{id}`, `POST /lineups/saved/{id}/generate?format=pdf|docx` — a saved lineup is a frozen snapshot (team/opponent name, per-player name/NSSZ) taken at creation time. Team/opponent/player can be supplied either as `source_*_id` (resolved from the live roster at save time) or as free text — **exactly one** of the two per field (`model_validator`s in `lineup/saved_lineups/schemas.py`; sending both is 422, so there is no "free text silently wins"). Duplicate NSSZ numbers in one lineup → 422 (`LineupRequest` validator; `_ensure_unique_nssz` in the saved-lineup service, on the resolved values, case-insensitive). Deleting the source team/player afterwards never changes an already-saved lineup.
- Text input: every string field uses the shared types in `lineup/common/types.py` (`CleanStr50/100/120/200`, `OptionalCleanStr*`): stripped, non-empty, length-capped, and no control characters (`Cc`, surrogates, U+FFFE/FFFF) because python-docx raises on them and tabs/newlines would shift the layout. Optional fields turn a blank into `None`. New text fields must use these types.
- Lists are ordered deterministically (`teams`: name, id; `players`/`saved_lineups`: created_at, id; pool: name, id) and saved-lineup snapshots by cap number (also on the create response: `repository.create_saved_lineup` refreshes the relationship).
- Pagination envelope: `{ "items": [...], "total": ..., "limit": ..., "offset": ... }` for all paginated list endpoints except `/teams/pool`.

### Key modules

Paths in this table are relative to `backend/`.

| File | Responsibility |
|------|---------------|
| `app.py` | FastAPI app entry point; lifespan calls `Base.metadata.create_all` unless `ENV=production` (Alembic handles DDL in prod); registers the 5 routers (health, lineups, teams, players, saved lineups); adds `CORSMiddleware` only when `CORS_ORIGINS` is set (`parse_cors_origins()`: explicit origins, `*` refused, exposes `Content-Disposition`, no credentials); initializes Sentry at import time if `SENTRY_DSN` is set (errors only, `traces_sample_rate=0.0`) |
| `main.py` | CLI entry point |
| `lineup/api/models.py` | Pydantic request models (`LineupRequest`, `PlayerRequest`); every string has `min_length=1` and a `max_length` matching the saved-lineup schemas (match/name/staff 200, division 100, team 120, date 50, NSSZ 50) |
| `lineup/common/types.py`, `lineup/common/errors.py` | Shared `CleanStr*` / `OptionalCleanStr*` input types (see Text input above); `handle_integrity_error` turns a stray `IntegrityError` (e.g. a team deleted between the service check and the commit) into `409` instead of 500, logging only exception class names because SQLAlchemy's message embeds names and NSSZ numbers. Registered in `app.py` |
| `lineup/health/router.py` | `GET /health` (liveness, no DB) and `GET /health?db=1` (readiness, `SELECT 1`). A failure is *returned* as `503 {"status":"unavailable"}`, not raised, so no driver text reaches the client and Sentry is not flooded. Used by the container healthcheck, CD and the keep-alive cron |
| `lineup/api/router.py` | `POST /lineups` endpoint (builds the DTO, delegates to `build_file_response`) |
| `lineup/api/file_response.py` | Shared by both generate endpoints: `FileFormat` enum, media types, `content_disposition()` (RFC 6266 `filename*` + ASCII fallback — header values are latin-1, so `ő`/`ű` would crash a plain `filename=`), `build_file_response()` (renders via `run_in_threadpool` so LibreOffice never blocks the event loop; `TimeoutExpired` → 504, other errors → 500) |
| `lineup/document/document_manager.py` | `.docx` read/write/style logic |
| `lineup/document/pdf_converter.py` | Converts docx bytes → PDF bytes via `libreoffice --headless` subprocess; uses a private per-call `-env:UserInstallation` profile and a 120s timeout (`CONVERSION_TIMEOUT_SECONDS`). Runs under `Popen(start_new_session=True)` and, on timeout, `os.killpg` kills the whole LibreOffice process group (`subprocess.run` would only kill the launcher and leak `soffice.bin`). A module-level `BoundedSemaphore` (`PDF_MAX_CONCURRENT`, default 2) caps parallel conversions; waiting more than `QUEUE_TIMEOUT_SECONDS` (10) raises `ConverterBusyError` → 503 in `file_response.py`. A missing `libreoffice` binary or a missing output PDF raise distinct `RuntimeError`s; stderr is decoded with `errors="replace"` and truncated |
| `lineup/water_polo/water_polo_lineup_creator.py` | Orchestrates template filling; exposes `create_document_bytes()` and `create_pdf_bytes()` |
| `lineup/water_polo/water_polo_lineup_dto.py` | `WaterPoloLineupDTO` and nested `WaterPoloLineupDTO.Player` data classes with builder pattern; `build()` requires match/division/team_name/cap/date/coach only — staff fields default to `""` (saved lineups may omit them) |
| `lineup/db/engine.py` | `DATABASE_URL` env var (default `sqlite+aiosqlite:///./lineup.db`); `get_session()` FastAPI dependency; `enable_sqlite_foreign_keys()` (SQLite-only, no-op on other dialects); `_make_engine_kwargs()` (`NullPool` for Postgres) — see notes below |
| `lineup/db/models.py` | `Team`, `Player`, `SavedLineup`, `LineupPlayerSnapshot` — see Data model note below |
| `lineup/auth/dependencies.py` | `get_current_user_id()` — always returns `None` pre-Auth; post-Auth, replace its body to extract the JWT `sub` claim, zero router/service changes needed |
| `lineup/teams/*.py`, `lineup/players/*.py`, `lineup/saved_lineups/*.py` | Standard `schemas.py`/`repository.py`/`service.py`/`router.py` layering per module |

**Data model** (see `documentation/Current-State-Backend.md` for the full ERD and rationale): `Team.players` and `SavedLineup.player_snapshots` are `relationship(..., lazy="selectin")` — async SQLAlchemy can't lazy-load relationships synchronously (raises `MissingGreenlet`), so eager `selectin` loading is required. A `SavedLineup` freezes `team_name`/`opponent_name`/`match_name` as plain text plus nullable soft FKs `source_team_id`/`source_opponent_id` → `teams.id` (`ondelete="SET NULL"`); each `LineupPlayerSnapshot` freezes `name`/`nssz_number`/`cap_number` plus a nullable soft FK `source_player_id` → `players.id` (`ondelete="SET NULL"`). `Player.team_id` → `teams.id` uses `ondelete="RESTRICT"` at the DB level, but team deletion is actually blocked earlier, at the service layer (409), so the DB-level RESTRICT never fires in practice.

**SQLite foreign key enforcement**: SQLite ignores `ondelete` clauses entirely unless `PRAGMA foreign_keys=ON` is set per-connection — `enable_sqlite_foreign_keys(engine)` in `lineup/db/engine.py` registers a SQLAlchemy `connect` event listener that sets this pragma; both the production engine and the test engine (`tests/conftest.py`'s `db_engine` fixture) call it. Without it, `SET NULL`/`RESTRICT` are silently inert. The listener is gated on `async_engine.url.get_backend_name() == "sqlite"` — `PRAGMA` is SQLite-only syntax and would fail every connection on Postgres.

**Postgres / Supabase connection notes**: there are two Supabase connection flavors. The app at runtime uses the *transaction pooler* (port 6543, user `postgres.<project-ref>`) with just `?ssl=require` on `DATABASE_URL`. `_make_engine_kwargs()` (Postgres only) adds `NullPool` since the pooler already pools, plus `connect_args` turning prepared statements off (`statement_cache_size=0` is asyncpg's own cache, `prepared_statement_cache_size=0` is SQLAlchemy's) and a `prepared_statement_name_func` giving each statement a unique name. All three are needed: without them the pooler hands one server connection to several clients and requests fail with `DuplicatePreparedStatementError` (found only by running against real Supabase; a `prepared_statement_cache_size=0` in the URL alone is NOT enough). An old URL that still carries `&prepared_statement_cache_size=0` is harmless. Also: `created_at` columns are `TIMESTAMP WITHOUT TIME ZONE`, so model defaults must be naive UTC (`_utcnow()` in `lineup/db/models.py`) — SQLite tolerates aware datetimes, asyncpg raises. SQLite-only tests can't catch this class of bug, so re-run the live smoke test (create team/player/saved lineup, delete) against the dev Supabase project after touching models or the engine. Alembic needs the *direct* connection (port 5432) — or the session-mode pooler if there's no IPv6 — because the transaction pooler can't run DDL; for Supabase that URL is `MIGRATE_DATABASE_URL` in the separate git-ignored `backend/.env.migrate` (never in `.env`, which Compose/`task serve` inject into the API's environment), used by `alembic/env.py` (preferred over `DATABASE_URL`) and `task migrate:supabase`. The `rls_and_least_privilege_role` migration (Postgres-only, guarded no-op on SQLite) enables RLS on every public table incl. `alembic_version`, revokes `anon`/`authenticated`, installs the `lineup_enable_rls` event trigger (skipped with a notice if not permitted) and creates the non-owner, NOBYPASSRLS `lineup_app` role (DML on the four app tables, interim `app_all` policy until #21); `task db:create-app-role` (`lineup/db/app_role.py`) then sets its password and rewrites the pooler `DATABASE_URL` to `lineup_app.<ref>`. **A new table's migration must add its own policy and grant the app role nothing more than it needs** — RLS denies the app until a policy exists. `alembic/env.py` skips *type* comparison on SQLite (UUID reflects as NUMERIC); CI's Postgres job compares types. `ENV=production` means "schema is Alembic-managed, skip `create_all`", not "the prod deployment": set it for any real Postgres, including the dev Supabase project (unset, the app would create untracked tables and the next `task migrate` would fail). The app stays on the pooler, not the direct connection: migrations are a separate manual step, the direct host is IPv6-only, and `NullPool` opens a connection per request, which is cheap via the pooler but wasteful directly against Postgres. Switching between SQLite and Postgres: `task db:postgres` / `task db:sqlite` (sed-based, in the Taskfile) comment/uncomment the filled-in pooler `DATABASE_URL` in `backend/.env` and add/remove `ENV=production`; `task db:status` reports the active one. `backend/.env.example` documents all of this; Docker Compose and `task serve` load `backend/.env`, but `task migrate`/`task migrate-new` deliberately don't (they default to SQLite, so a migration never hits Supabase by accident; pass `DATABASE_URL` for one run). Only a dev Supabase project exists so far; prod project, real auth and RLS are tracked separately (see `documentation/Roadmap-Backend.md`).

**Coverage + async SQLAlchemy gotcha**: `coverage.py` needs `concurrency = ["greenlet", "thread"]` under `[tool.coverage.run]` in `pyproject.toml` — SQLAlchemy's async ORM bridges sync calls onto greenlets (`greenlet_spawn`), and without this setting, `coverage` silently drops line hits for code *after* a greenlet-based await resumes (e.g. the line right after `await session.commit()`), even though the code genuinely ran. This looked like a real ~90%-coverage shortfall across every DB-touching module until traced to this missing config.

### Container

- `backend/Dockerfile`: two stages, both `python:3.13-slim` **pinned by digest** (Dependabot's docker ecosystem bumps tag + digest). *builder* installs the deps with the pinned `uv` image (`uv sync --frozen --no-dev`, bytecode-compiled); *runtime* adds `libreoffice-writer-nogui` (no GUI stack; fidelity verified by the e2e suite), `tini` as PID 1 (`ENTRYPOINT ["tini", "--"]`, reaps `soffice.bin` children, instant `docker stop`) and the fonts, then copies the venv in. uv is not in the final image. Runs as the non-root `app` user (uid 10001, owns `/app` so the default SQLite file can be written; `HOME=/home/app`). `HEALTHCHECK` polls `GET /health` (liveness only, so a DB outage doesn't restart the container) with the interpreter, since curl isn't installed. `PYTHONUNBUFFERED=1`. Image size went from ~1.16 GB to ~870 MB
- Fonts: `--no-install-recommends` is kept, so the metric-compatible font packages are installed explicitly — `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea` (Cambria), `fonts-liberation2` (Arial/Times/Courier). `backend/docker/fontconfig/99-calibri-carlito.conf` (copied to `/etc/fonts/conf.d/`) forces Calibri → Carlito, and `fc-cache -f` refreshes the cache. These are what make the PDF match the source `.docx`.
- The Docker build context is `backend/` (`docker build -t lineup backend` in the Taskfile), so repo-root items (`.github/`, `.claude/`, `documentation/`, `frontend/`, `compose.yml`, `Taskfile.yml`) can never enter the image. `backend/.dockerignore` is a security control: the Dockerfile does `COPY . .`, so it must exclude `.env`/`.env.*` (`backend/.env` holds the Supabase credentials and now sits *inside* the context) and `*.db`, alongside tests, `*.md`, caches, `.git`. Add any new secret/local-state file to it. Because `tests/` is excluded the image ships without tests — that's why the e2e suite runs from the host against the running container, not inside the image.
- `CMD` runs `uvicorn` straight from `/app/.venv/bin` (on `PATH`): no `uv` at runtime, so no writable cache/`HOME` needed for it.
- `compose.yml` (repo root): single `api` service using the pre-built `lineup` image (not `build:`), with `cap_drop: [ALL]` and `no-new-privileges` (LibreOffice needs neither); the image's `HEALTHCHECK` is inherited, and `task test-e2e` starts it with `docker compose up -d --wait`. It gets its settings from `env_file: backend/.env` with `required: false` (Compose >= 2.24) — compose's own `.env` interpolation only looks next to `compose.yml`, so it would silently stop seeing `backend/.env`. With no `backend/.env` the container falls back to its in-container SQLite default.
- `task build` / `task rebuild` builds the image; `task up` / `task down` starts/stops it; containers can be monitored using `lazydocker`
- CI's `e2e` job scans the built `lineup:latest` image with `aquasecurity/trivy-action` (severity `CRITICAL,HIGH`) after `task test-e2e` runs — report-only (`exit-code: "0"`, never fails the build), since the LibreOffice + apt package surface has more CVEs than can realistically be kept at zero. Results go to the job log (table format) and the repo's Security → Code scanning tab (SARIF upload via `github/codeql-action/upload-sarif`).

---

## Development Workflow

```
task install    # uv sync — install dependencies
task test       # pytest with coverage (must pass at 100%; e2e tests excluded)
task test-e2e   # build image, start container, run real-conversion fidelity tests, tear down
task lint       # ruff check
task format     # ruff format
task serve      # local uvicorn dev server, loads backend/.env (no PDF support — no LibreOffice; DB tables auto-created on startup unless ENV=production)
task db:status  # show whether backend/.env selects SQLite or the Supabase pooler
task db:postgres  # switch backend/.env to the Supabase pooler (DATABASE_URL + ENV=production)
task db:sqlite  # switch backend/.env back to local SQLite
task run        # run main.py (CLI demo, writes resources/modified_rajtlista.docx)
task build      # build container image (lineup)
task rebuild    # force fresh build with --no-cache
task up         # start container in detached mode
task down       # stop container
task migrate    # apply Alembic migrations (upgrade head)
task migrate-new -- -m "description"  # autogenerate a new migration
task migrate-down  # rollback one migration step
task migrate-check  # throwaway SQLite: upgrade head + `alembic check` (CI runs it)
task migrate:supabase  # upgrade head using MIGRATE_DATABASE_URL from backend/.env.migrate (owner creds)
task db:create-app-role  # generate lineup_app's password, rewrite backend/.env's pooler URL (never printed)
task docs:references  # regenerate the dependency block in documentation/References.md
task docs:check   # fail if that block is stale (CI runs it)
```

Environment variables (`DATABASE_URL`, `ENV`, `CORS_ORIGINS`, `PDF_MAX_CONCURRENT`, `SENTRY_DSN`) are documented in `backend/.env.example` — copy it to `backend/.env` (git-ignored; a future `frontend/.env` is separate) to opt into Postgres/Supabase; with no `backend/.env` everything runs on local SQLite.

`SENTRY_DSN` (optional env var, unset by default): when set, `app.py` initializes Sentry error monitoring at import time (errors only, no performance tracing). Never set locally/in CI/tests — leaving it unset means `sentry_sdk.init()` is never called and nothing is sent anywhere.

### Branches and environments

Two environments only (dev + prod, no separate test env), so two long-lived branches:

- **`develop`** — the default branch and integration branch. Feature/fix branches (`feat/<issue>-…`, `fix/…`, `chore/…`) are cut from it and PR'd back into it. Will deploy to the dev environment once CD exists (#8). Dependabot PRs target it, and `wiki-sync.yml` publishes `documentation/` from it.
- **`main`** — production. Only changes via a release PR `develop` → `main` (later: prod deploy + version tag, #17). A hotfix branches off `main`, is PR'd into `main`, then `main` is merged back into `develop`.
- Both are protected: changes go through PRs with green `Lint & test`, `E2E (real PDF conversion)`, `Docs updated` and `Migrations (Postgres)`; no force-pushes or deletions. GitHub can't restrict which branch a PR into `main` comes from, so "only from `develop` (or a hotfix)" is a convention.
- **PRs are merged with a merge commit** (`gh pr merge --merge`), never squash or rebase, so each branch commit and its `#N` reference stays in history, and `git branch -d` works after the merge. Keep branch history clean by amending instead: `git commit --amend` for the last commit, `git commit --fixup=<sha>` + `git rebase --autosquash origin/develop` for an earlier one. After a push, that means `git push --force-with-lease`, on feature branches only. GitHub deletes the remote branch on merge.

---

### Claude Code skills (`.claude/skills/`)

`repo-audit` (opus): full audit → GitHub reconciliation. `compliance-audit` (opus): GDPR/Hungarian/OWASP checks against its `requirements.md`; full audit → compliance matrix → issues, or `quick <issue#|branch>` per feature (run at issue start and as a `create-pr` gate). `new-issue` (haiku): issue conventions, labels/milestone/board/relations recipes. `triage-dependabot` (sonnet): the pre-PR Dependabot rule above. `create-pr` (sonnet): gates + PR. `supabase-smoke` (haiku): the live dev-Supabase smoke test. Also `update-documentation` and `setup-project`. The models are pinned with `model:` in each skill's frontmatter and apply only while the skill runs. If you change a workflow these skills encode (labels, milestones, epics, board fields, the Dependabot rule, the smoke-test steps), update the skill in the same change. `.claude/settings.json` (shared) allows `task lint`/`task test` and denies reading `.env*` at the root and `backend/.env*`; `.claude/settings.local.json` is personal and git-ignored.

## Conventions

### Security (ruff `S` / flake8-bandit)

Paths are relative to `backend/`.

- `[tool.ruff.lint] extend-select = ["S", "D1"]` in `pyproject.toml` enables flake8-bandit checks and pydocstyle's *missing docstring* checks (D100-D107 only, no style rules) as part of `task lint`. `tests/**` and `alembic/versions/*.py` are exempt from `D1`.
- `per-file-ignores` suppresses `S101` (`assert`) and `S310` (`urlopen` scheme check) for `tests/**` — both are expected patterns in test code (pytest's `assert` idiom; `S310` flags a fixed local `BASE_URL` constant, never user input), not real risks.
- `per-file-ignores` also suppresses `S603`/`S607` (subprocess call / partial executable path) for `lineup/document/pdf_converter.py` specifically — its one `subprocess.run([...])` call uses a literal `"libreoffice"` executable and an argv list with no `shell=True`, and every other argument is either a fixed flag or built from a `tempfile.TemporaryDirectory()` the process created itself, so neither warning reflects a real vulnerability there. Don't remove this ignore to "fix" the warning without addressing why it was added — re-read this note first.
- If a *new* `S`-rule violation appears anywhere outside these two ignored spots, treat it as a real finding: fix the underlying code rather than reflexively adding another ignore.

### Tests

Paths below are relative to `backend/` (run pytest from there — `task test` does).

- `pyproject.toml` enforces `fail_under = 100`
- Every new module needs a corresponding `tests/test_<module>.py`
- Any code that calls LibreOffice must mock `PdfConverter.convert` — it is not available locally. `tests/test_pdf_converter.py` mocks `subprocess.Popen` (and `shutil.which`); its one real-process test uses a fake `libreoffice` shell script that forks a child, to prove the group kill reaches it (Linux `/proc` only)
- Tests for API endpoints that trigger PDF conversion use an `autouse` fixture in `test_api.py` (and in `TestGenerateFromSavedLineup` in `test_saved_lineups.py`) that patches `PdfConverter.convert`. To force a rendering failure, patch `lineup.api.file_response.WaterPoloLineupCreator` — that's where both endpoints construct it now
- `tests/test_pdf_conversion_e2e.py` is the exception: it drives the **real** conversion against the running container. It is marked `e2e` and excluded from `task test` by `addopts = "-m 'not e2e'"` (so it never affects coverage); run it via `task test-e2e`. It talks to the API over HTTP (stdlib `urllib`) and validates layout with `pdfplumber` — asserting a single page, expected text, and that word widths/positions match `expected-rajtlista.pdf`. It does **not** pixel-diff (the reference uses real Calibri, the container uses metric-compatible Carlito).
- DB tests use the `async_client` fixture (`tests/conftest.py`) — a fresh in-memory SQLite DB per test, with `get_session` and `get_current_user_id` dependency-overridden (`get_current_user_id` always yields `None`, matching pre-Auth production behavior).
- The `owner_id`/`user_id`-scoped filtering branches in `teams/players/saved_lineups` repositories can't be reached through the API yet (since `get_current_user_id()` always returns `None`) — they're tested directly against the `db_session` fixture instead, calling repository functions with real non-`None` IDs.
- `[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet", "thread"]` — required for accurate coverage of any code that calls SQLAlchemy's async ORM. Don't remove it; without it, coverage under-reports on lines following an `await session.commit()`/`.refresh()`/etc. even though they actually ran.
- `tests/test_postgres_migrations.py` asserts RLS/role/grant behaviour against a real Postgres; it is **skipped** unless `POSTGRES_TEST_URL` is set (a throwaway, empty DB — CI's `Migrations (Postgres)` job sets it; locally run a `postgres:17` container). `tests/test_app_role.py` covers the password/`.env` rewriting with a fake engine (no DB).
- `tests/test_app.py` covers both branches of `app.py`'s Sentry init (`SENTRY_DSN` set/unset) by mocking `sentry_sdk.init` and `importlib.reload`-ing the `app` module under each env state. Safe to reload freely: `tests/conftest.py` imports `app` once at collection time and keeps its own reference, so a later reload elsewhere doesn't retroactively affect the `client`/`async_client` fixtures. Note `[tool.coverage.run] source = ["lineup"]` doesn't include `app.py`, so this file's coverage isn't actually gated by `fail_under = 100` — the tests exist for correctness, not the coverage requirement.

### OpenAPI / FastAPI

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's query parameter introspection
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to appear in the docs
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI renders enums from `$ref` correctly
- The endpoint is annotated `-> Response` for its raw binary file output — this does **not** suppress query-parameter display; the `format` param still appears in the OpenAPI spec (verified via `/openapi.json`). FastAPI derives query params from the function signature, not the return annotation.

### Container image

- `compose.yml` uses `image: lineup`, not `build:` — so `task build`/`task rebuild` is always needed before `task up`
- To fully reset: `task down` → `docker rmi lineup` → `docker image prune` → `task rebuild` → `task up`

---

## Project Structure

```
lineup/
├── Taskfile.yml
├── compose.yml                       # image: lineup; env_file backend/.env (optional)
├── PLAN.md                           # dev-preview plan + progress log (FE, auth, invitations, dev deploy)
├── README.md  CLAUDE.md
├── .github/                          # CI (ci.yml, docs-check.yml, wiki-sync.yml), PR template, dependabot.yml
├── .claude/                          # settings.json, skills/, commands/
├── documentation/                    # mirrored into the GitHub wiki by CI (incl. Newcomer-Guide.md, References.md)
├── scripts/                          # check_docs_touched.sh (docs gate), docs_references.py (generates References.md block)
├── frontend/
│   └── DESIGN.md                     # Polaris theme spec (shadcn tokens) — the app itself is not scaffolded yet
└── backend/                          # everything Python; run Python commands with this as cwd
    ├── app.py
    ├── main.py
    ├── pyproject.toml  uv.lock  .python-version
    ├── Dockerfile  .dockerignore
    ├── .env.example                      # documents DATABASE_URL / ENV / CORS_ORIGINS / PDF_MAX_CONCURRENT / SENTRY_DSN (copy to git-ignored backend/.env)
    ├── docker/
    │   └── fontconfig/
    │       └── 99-calibri-carlito.conf   # Calibri → Carlito mapping, copied into the image
    ├── resources/
    │   └── rajtlista.docx
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       ├── 35ce55ceabf4_initial_schema.py   # single squashed migration — teams/players/saved_lineups/lineup_player_snapshots
    │       └── 8b1f3c2d9a47_rls_and_least_privilege_role.py   # Postgres-only: RLS, revokes, event trigger, lineup_app role
    ├── lineup/
    │   ├── api/
    │   │   ├── models.py
    │   │   ├── file_response.py   # FileFormat, content_disposition(), build_file_response()
    │   │   └── router.py
    │   ├── document/
    │   │   ├── document_manager.py
    │   │   └── pdf_converter.py
    │   ├── water_polo/
    │   │   ├── water_polo_lineup_creator.py
    │   │   └── water_polo_lineup_dto.py
    │   ├── db/
    │   │   ├── base.py       # DeclarativeBase
    │   │   ├── engine.py     # get_session(), enable_sqlite_foreign_keys(), _make_engine_kwargs()
    │   │   ├── app_role.py   # `task db:create-app-role`: lineup_app password + .env rewrite
    │   │   └── models.py     # Team, Player, SavedLineup, LineupPlayerSnapshot
    │   ├── auth/
    │   │   └── dependencies.py   # get_current_user_id() — None pre-Auth
    │   ├── common/
    │   │   ├── types.py      # CleanStr* / OptionalCleanStr* input types
    │   │   └── errors.py     # IntegrityError -> 409 handler
    │   ├── health/
    │   │   └── router.py     # GET /health, /health?db=1
    │   ├── teams/
    │   │   ├── schemas.py
    │   │   ├── repository.py
    │   │   ├── service.py
    │   │   └── router.py
    │   ├── players/
    │   │   ├── schemas.py
    │   │   ├── repository.py
    │   │   ├── service.py
    │   │   └── router.py
    │   └── saved_lineups/
    │       ├── schemas.py
    │       ├── repository.py
    │       ├── service.py
    │       └── router.py
    └── tests/
        ├── resources/
        │   ├── expected_rajtlista.docx
        │   └── expected-rajtlista.pdf     # reference render for the e2e fidelity test
        ├── conftest.py
        ├── test_api.py
        ├── test_app.py
        ├── test_document_manager.py
        ├── test_pdf_converter.py
        ├── test_pdf_conversion_e2e.py     # e2e: real conversion vs the running container
        ├── test_water_polo_lineup_creator.py
        ├── test_water_polo_lineup_dto.py
        ├── test_auth_dependencies.py
        ├── test_health.py                 # /health liveness + readiness
        ├── test_app_role.py               # lineup.db.app_role (password + .env rewrite, fake engine)
        ├── test_postgres_migrations.py    # RLS / roles / grants on a real Postgres (skipped without POSTGRES_TEST_URL)
        ├── test_input_hardening.py        # control chars/blanks, unknown team_id, source-or-text, duplicate NSSZ, ordering
        ├── test_docs_tooling.py           # scripts/ (References generator, docs gate) + wiki PAGE_MAP completeness
        ├── test_db_engine.py
        ├── test_db_models.py
        ├── test_teams.py
        ├── test_players.py
        └── test_saved_lineups.py
```
