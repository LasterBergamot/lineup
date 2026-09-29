> **Temporary planning doc.** Delete this file once the implementation described below has shipped and merged — it's a working plan, not a permanent doc (permanent docs live under `documentation/`).

# Plan: Supabase dev-env DB cutover (#6) + Dependabot-alert check in CLAUDE.md

## Context

Issue [#6 "Introduce Supabase"](https://github.com/LasterBergamot/lineup/issues/6) covers both Postgres DB hosting and OAuth. The goal is to move forward now so the **dev environment** (issue #13's goal) has a real Postgres backend to develop against, but this pass is explicitly scoped to **DB cutover only** — `get_current_user_id()` stays returning `None`; the roadmap doc (`documentation/Roadmap-Backend.md`) itself sequences `team_members`/`team_invitations` (#19) before the auth swap, and #19 hasn't shipped, so wiring real JWT validation now would be out of order and would make pre-existing `NULL`-owned rows invisible with no way yet to grant access. Only a **dev** Supabase project is created this pass; the prod project is deferred to pair with #8 (CD).

A real bug was found during investigation: `lineup/db/engine.py`'s `enable_sqlite_foreign_keys()` unconditionally registers a `connect` listener that runs `PRAGMA foreign_keys=ON` — SQLite-only syntax. Pointed at a real Postgres/Supabase connection, every connection would fail with a syntax error. This must be dialect-gated as part of the cutover, not just have `DATABASE_URL` swapped.

Separately, add an instruction to `CLAUDE.md` so Claude Code checks GitHub Dependabot alerts before opening a PR in this repo. Confirmed `gh api repos/LasterBergamot/lineup/dependabot/alerts` already works read-only in this environment (0 open alerts currently, 4 historical, all `state: fixed`) — this is a pure `CLAUDE.md` process-instruction addition, no GitHub Action needed.

Any local code change goes on a new branch, following this repo's existing convention (e.g. past `feature/16-security-scanning-and-logging`): **`feature/6-introduce-supabase`**.

---

## Manual steps (user performs, external to this repo)

1. In the Supabase dashboard, create one new project named **`lineup-dev`** (any region), with a strong generated DB password stored in a password manager.
2. From **Project Settings → Database → Connection string**, record both:
   - **Direct/session** connection (port `5432`, `db.<project-ref>.supabase.co`) — for Alembic migrations only.
   - **Transaction pooler / Supavisor** connection (port `6543`, `aws-0-<region>.pooler.supabase.com`, user `postgres.<project-ref>`) — for app runtime.
3. From **Project Settings → Data API**, note the `anon`/`service_role` keys and the JWT secret — **write these down but don't use them yet** (they're for the later auth swap, #19-adjacent work).
4. Do **not** enable RLS or configure the Google OAuth provider yet — both remain deferred per the roadmap's own sequencing.
5. Paste the two connection strings into a local `.env` (created from the new `.env.example`, see below) — never commit real credentials.

### Credential recovery

Nothing here is a permanent single point of failure as long as Supabase account/org access is retained:
- **DB password lost**: Project Settings → Database → "Reset database password" generates a new one with no data loss — just update the stored connection strings afterward.
- **anon key / service_role key / JWT secret**: always re-viewable in Project Settings → Data API / JWT Settings by anyone with dashboard access; not "lost" unless dashboard access itself is lost. All are rotatable if a leak is ever suspected (rotating the JWT secret invalidates previously-issued tokens — relevant once auth is wired in, not this pass).
- **The actual unrecoverable scenario**: losing access to the Supabase account/org itself (e.g. single personal account, no backup). Mitigate by adding a second org member/owner and keeping the account's recovery email + 2FA backup codes stored safely (e.g. in the same password manager).

This note gets written into the docs (see Documentation section below), not just left here.

---

## Code changes

### `lineup/db/engine.py` — dialect-gate the SQLite pragma + add Postgres pool handling

- `enable_sqlite_foreign_keys()`: return early unless `async_engine.url.get_backend_name() == "sqlite"` — fixes the crash-on-Postgres bug.
- Add a small `_make_engine_kwargs(database_url)` helper: returns `{"poolclass": NullPool}` for `postgresql` URLs (required in front of Supabase's transaction-mode pooler, which already does its own pooling), `{}` otherwise. Pass `**_make_engine_kwargs(DATABASE_URL)` into `create_async_engine(...)`.
- No SSL/prepared-statement Python code needed — those are query-string params on `DATABASE_URL` itself (`?ssl=require&prepared_statement_cache_size=0`), documented in `.env.example`. Keeps SQLite path byte-for-byte unchanged.

### `pyproject.toml`

- Add `"asyncpg>=0.30"` to `[project] dependencies` (matches the version floor already specified in `documentation/Roadmap-Backend.md`). Run `uv lock` after.

### `.env.example` (new file)

Document, with both lines present but commented out so the SQLite default stays active unless explicitly opted in:
- `DATABASE_URL` — SQLite default (commented, matches the Python-side default already in `engine.py`), plus two Postgres examples (pooler for app runtime, direct for `task migrate`), each annotated with which one to use when.
- `ENV` — note that `production` here means "Alembic-managed schema", not "this is the prod deployment"; set it whenever `DATABASE_URL` points at any real Postgres/Supabase instance, dev or prod alike.
- `SENTRY_DSN` — existing var, left blank, with the existing "never set locally" note.

Add `.env` to `.gitignore` (currently has no `.env` entry at all).

### `compose.yml`

Add an `environment:` block using Compose's `${VAR:-default}` interpolation so `DATABASE_URL`/`ENV`/`SENTRY_DSN` reach the container, defaulting to today's exact behavior when no `.env` exists:
```yaml
environment:
  - DATABASE_URL=${DATABASE_URL:-sqlite+aiosqlite:///./lineup.db}
  - ENV=${ENV:-}
  - SENTRY_DSN=${SENTRY_DSN:-}
```

### Tests — `tests/test_db_engine.py`

Add (keeping the existing `test_get_session_yields_async_session` untouched):
- `test_enable_sqlite_foreign_keys_registers_listener_for_sqlite` — asserts the `connect` listener *is* registered for a `sqlite+aiosqlite://` engine.
- `test_enable_sqlite_foreign_keys_is_noop_for_postgres` — asserts it's *not* registered for a `postgresql+asyncpg://` engine (constructing this engine is safe/no-network — SQLAlchemy async engines are lazy until `.connect()`/`.begin()` is awaited).
- `test_make_engine_kwargs_uses_nullpool_for_postgres` / `test_make_engine_kwargs_empty_for_sqlite`.

This keeps the 100%-coverage gate satisfied for both new branches without needing a real Postgres server in CI (consistent with the existing "mock what CI can't run" convention, e.g. `PdfConverter.convert`).

### Future schema migrations (note for later reference)

Once this ships, changing the schema again later (e.g. adding `team_members`/#19) works the same way regardless of backend:
1. Edit the SQLAlchemy models in `lineup/db/models.py`.
2. `task migrate-new -- -m "description"` — autogenerates a new Alembic revision by diffing models against the current DB. **Run this against the SQLite dev DB** (default `DATABASE_URL`, no env override needed) so autogeneration doesn't require live Supabase access.
3. Review the generated file under `alembic/versions/` by hand — autogenerate is a starting point, not ground truth (e.g. it won't infer `ondelete=` behavior changes reliably).
4. `task migrate` applies it locally (SQLite). To apply the same migration to the Supabase dev project, export `DATABASE_URL` to the **direct/session** connection string first (the transaction pooler doesn't support the DDL/advisory-lock operations Alembic needs) and run `task migrate` again. `task migrate-down` rolls back one revision the same way.
5. This note goes into `documentation/Current-State-Backend.md` (see below) so it isn't lost.

### Future *technology* migration — moving off Supabase/Postgres entirely (note for later reference)

Distinct from the Alembic note above: this covers moving to a different DB engine, cloud provider, or hosting stack later, not routine schema changes. Goes into `documentation/Current-State-Backend.md` as a "Portability" note:

- **Moving to a different Postgres host** (AWS RDS, Neon, Render, self-hosted, etc.), staying on Postgres: cheapest move by far. `DATABASE_URL` is already the only coupling point for the app layer (`lineup/db/engine.py`) — point it at the new host and nothing else in the app changes. Two things are Supabase-specific and need re-checking on a new host: (1) the `NullPool`/`prepared_statement_cache_size=0` query-string settings this pass adds are needed for *any* PgBouncer-style transaction pooler, not Supabase specifically — keep them only if the new host also fronts Postgres with a transaction-mode pooler, drop them if connecting directly; (2) once the follow-up issue's auth swap and RLS (#21) land, both are Supabase-flavored: `get_current_user_id()` would validate Supabase-issued JWTs (swappable, same single-function seam already used for the pre-Auth stub), and RLS policies are plain Postgres SQL (`ENABLE ROW LEVEL SECURITY`/`CREATE POLICY`) that carries over to any Postgres host unchanged.
- **Moving to a non-Postgres relational DB** (e.g. MySQL): needs a different async driver dependency (`aiomysql`/`asyncmy` instead of `asyncpg`) and re-running the Alembic migration chain against the new engine to (re)create schema — Alembic manages DDL, not data, so existing **data** would need a separate export/import pass (e.g. read rows via the old SQLAlchemy engine, write via the new one), not just a migration replay. RLS policies have no equivalent in most non-Postgres engines and would need reimplementing as application-level authorization checks instead.
- **Moving hosting/cloud stack** while staying on Postgres (e.g. off Fly.io): mostly an ops exercise — the container image and `compose.yml` are already host-agnostic. The only real coupling is Auth (JWT issuer) and RLS, both discussed above.

---

## Documentation updates

Broader than just the DB cutover: a full pass so a newcomer could understand the whole app and codebase from the docs alone, not just an accurate changelog-style update. Scope:

- **`README.md`** — expand into a genuine onboarding doc: what the project does and why (document generation + persistence layer), an architecture walkthrough (request → template fill → optional LibreOffice PDF conversion; and separately, the Teams/Players/SavedLineups CRUD layer and how it's structured), full setup instructions, an "Environment variables" section (`.env.example`, `DATABASE_URL` SQLite vs. Supabase forms, `ENV`, `SENTRY_DSN`, plus the credential-recovery note from above), a walkthrough of the API surface with example requests, the dev workflow (`task` commands), and an updated project-structure tree including `.env.example`. Written so someone with zero prior context on this repo can go from clone to understanding "how does a request actually get handled" without reading source first.
- **`documentation/Current-State-Backend.md`** — new subsection on the dialect-gated DB engine (as previously planned), plus the "Future schema migrations" note above, plus expand terse existing sections with enough explanation (not just facts) for a newcomer to follow the data model and request flow.
- **`documentation/Current-State-Frontend.md`, `documentation/Current-State-Everything-Else.md`, `documentation/Roadmap-*.md`, `documentation/Home.md`** — pass over each for the same newcomer-clarity bar; fix the stale `in-memory-db-plan.md` references (that file doesn't exist anywhere in the repo or its git history) to point at `documentation/Current-State-Backend.md` / `Roadmap-Backend.md` instead; shrink `Roadmap-Backend.md` step 2 to the remaining prod-only piece and add a footnote that the dev cutover (#6, this work) is independent of the auth/RLS rollout sequence.
- **`.claude/skills/update-documentation/SKILL.md`** — fix its 3 stale `in-memory-db-plan.md` mentions (agent-instruction file, not user-facing, but actively misleading as-is).
- **`CLAUDE.md`**:
  - New bullet at the end of `## Instructions`: `- Before creating a PR in this repo, check for open GitHub Dependabot alerts via \`gh api repos/LasterBergamot/lineup/dependabot/alerts\` (filter for \`"state": "open"\`) and surface any findings to the user.`
  - New bullet: documentation updates (README + `documentation/`) should be written so a newcomer with no prior context can understand the architecture and codebase from them, not just record what changed — this pass is the baseline; keep it that way going forward.
  - Fix the two stale `in-memory-db-plan.md` references (lines 21, 61).
  - Update the `lineup/db/engine.py` row in Key Modules, and add a short "Postgres/Supabase connection notes" callout paralleling the existing "SQLite foreign key enforcement" one (NullPool, `prepared_statement_cache_size=0`, direct-vs-pooler URLs, the `ENV=production` convention).
  - Add a line under Development Workflow pointing at `.env.example`.

---

## Follow-up issue for remaining Supabase scope

Since only the dev DB cutover ships here, create a new GitHub issue for what's left of #6, so it doesn't get lost:

- **Title**: "Finish Supabase integration: prod project, auth JWT swap, and prod DATABASE_URL cutover"
- **Body** covers: creating the `lineup-prod` Supabase project; enabling the Google OAuth provider; swapping `get_current_user_id()` to validate a real Supabase JWT (per `documentation/Roadmap-Backend.md`'s sequencing, this is blocked on #19 landing first); deciding the ownership-backfill strategy for pre-existing `NULL` `owner_id`/`user_id` rows once the swap happens; adding `NOT NULL` (and considering an `auth.users` FK) to those columns; wiring the prod `DATABASE_URL` + secrets into CD (#8).
- **Linking**: reference #6 (parent/split-from), note it's blocked by #19, and that it blocks #8 and #21 (RLS meaningfully depends on real auth existing) — plain issue-number references in the body auto-link on GitHub.
- Leave issue #6 **open** (don't close it) — this PR only partially addresses it. Use "Partially addresses #6" (not "Closes #6") in the PR description so merging doesn't auto-close it.
- Created via `gh issue create` once this plan is picked back up and approved (issue creation is a state-changing `gh` action — not done preemptively).

---

## Sequencing

1. `git checkout main && git pull && git checkout -b feature/6-introduce-supabase`
2. Supabase dashboard setup (manual, can happen in parallel with step 3).
3. Code changes (`engine.py`, `pyproject.toml`+`uv lock`, `.env.example`, `.gitignore`, `compose.yml`) + tests.
4. `task lint && task test` — must stay green/100% against the untouched SQLite default.
5. Docs updates (README + all of `documentation/` + CLAUDE.md, per the expanded scope above).
6. Manual verification against real Supabase (below), then flip back to SQLite and re-confirm.
7. CLAUDE.md Dependabot bullet — dogfood it once (`gh api repos/LasterBergamot/lineup/dependabot/alerts`) before opening the PR.
8. Create the follow-up GitHub issue for the remaining Supabase scope, linked to #6/#8/#19/#21 as described above.
9. Delete this file (`supabase-dev-cutover-plan.md`) once everything above has shipped and merged.

## Verification

**Automated regression (SQLite, unchanged default):**
- `uv sync`, `task lint`, `task format`, `task test` (100% coverage including new engine tests).
- `task serve` and `task build && task up` with no `.env` present — confirm identical behavior to today, then `task down`.

**Manual, against the real `lineup-dev` Supabase project (not automatable):**
1. Create `.env` from `.env.example`; export the **direct** URL; `ENV=production task migrate` — confirm `alembic upgrade head` succeeds and all 4 tables + `alembic_version` appear in Supabase's Table Editor.
2. Switch `.env` to the **pooler** URL (`ssl=require&prepared_statement_cache_size=0`), keep `ENV=production`, run `task serve` — confirm no `PRAGMA` syntax error (proves the dialect gate works against a real server) and `POST /teams`/`GET /teams` succeed, with the row visible in Supabase's Table Editor.
3. Repeat via `task build && task up` (containerized path, compose auto-loads `.env`).
4. **Switch back**: comment out the Postgres lines in `.env` (or delete it), restart — confirm the app falls back to local SQLite cleanly, proving the toggle is bidirectional, not a one-way migration.
5. Re-run `task test`/`task test-e2e` afterward to confirm neither reads the real `.env` or was affected.
