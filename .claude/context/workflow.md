# Development workflow, environment variables, branches

Run the tasks from anywhere in the repo (`Taskfile.yml` sets the working directory).

## Tasks

```
task install    # uv sync — install dependencies
task doctor     # check required tools + minimum versions (scripts/doctor.sh; the setup runbook is documentation/Setup.md)
task test       # pytest with coverage (must pass at 100%; e2e tests excluded)
task test-e2e   # build image, make a throw-away JWT key, start container (+ compose.e2e.yml JWKS sidecar), run real-conversion fidelity tests, tear down
task lint       # ruff check
task format     # ruff format
task serve      # local uvicorn dev server, loads backend/.env (no PDF support — no LibreOffice; DB tables auto-created on startup for SQLite via AUTO_CREATE_SCHEMA=1)
task db:status  # show whether backend/.env selects SQLite or the Supabase pooler
task db:postgres  # switch backend/.env to the Supabase pooler (DATABASE_URL + ENV=production)
task db:sqlite  # switch backend/.env back to local SQLite (comments the pooler URL out, keeps it)
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
task db:create-app-role  # generate lineup_app's password, rewrite backend/.env's pooler URL (never printed); asks for a typed `yes` first (`-- --yes` skips it) because a re-run rotates the password: update the Fly DATABASE_URL and KEEPALIVE_DATABASE_URL secrets afterwards
task fe:install   # pnpm install --frozen-lockfile in frontend/
task fe:dev       # Vite dev server on :5173, proxies /api to the container from task up
task fe:lint      # ESLint + Prettier check
task fe:format    # Prettier write
task fe:typecheck # tsc --noEmit
task fe:test      # Vitest (fast loop)
task fe:coverage  # Vitest + coverage report; fails below 100 % (CI runs this one)
task fe:e2e       # Playwright at phone + desktop size, network mocked (LINEUP_CHROMIUM=/usr/bin/chromium to use an installed browser)
task fe:build     # tsc + vite build into frontend/dist
task fe:api       # regenerate frontend/src/api (openapi.json + schema.d.ts) from the backend's OpenAPI spec
task fe:api:check # fail if that generated client is stale (CI runs it)
task fe:check     # lint + coverage + build + api:check, i.e. the CI Frontend job
task release:bump -- patch|minor|major|X.Y.Z  # bump the version in backend/pyproject.toml + frontend/package.json (scripts/bump_version.py), then task fe:api; commit it in a PR, then run the Release workflow
task docs:references  # regenerate the dependency block in documentation/References.md
task docs:check   # fail if that block is stale (CI runs it)
```

## Environment variables

Environment variables (`DATABASE_URL`, `ENV`, `AUTO_CREATE_SCHEMA`, `CORS_ORIGINS`, `SUPABASE_URL`, `APP_BASE_URL`, `PDF_MAX_CONCURRENT`, `DOCS_ENABLED`, `MAX_BODY_BYTES`, `RATE_LIMIT_GENERATE_PER_USER`, `RATE_LIMIT_GENERATE_PER_IP`, `CLIENT_IP_HEADER`, `SENTRY_DSN`) are documented in `backend/.env.example` — copy it to `backend/.env` (git-ignored; the frontend's public `VITE_*` settings, including `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`, live in the separate `frontend/.env`, see `frontend/.env.example`) to opt into Postgres/Supabase; with no `backend/.env` everything runs on local SQLite.

`ENV=production` also makes startup fail closed (`validate_production_config()`: needs a `postgresql+asyncpg` `DATABASE_URL` with `ssl=require`/`verify-full` and `SUPABASE_URL`) and turns the API docs off, so health checks and scripts must use `GET /health`, not `/docs`. On Fly.io `CLIENT_IP_HEADER=Fly-Client-IP` is already set in `backend/fly.toml`; `DATABASE_URL`, `SUPABASE_URL` and `CORS_ORIGINS` are Fly secrets (`fly secrets set`), never in `fly.toml`. Setup and deploy steps: `documentation/Fly-Setup.md`. The frontend origin (the Cloudflare Pages URL, `documentation/Pages-Setup.md`) has to be in `CORS_ORIGINS`, exact match.

`SENTRY_DSN` (optional env var, unset by default): when set, `app.py` initializes Sentry error monitoring at import time (errors only, no performance tracing). Never set locally/in CI/tests — leaving it unset means `sentry_sdk.init()` is never called and nothing is sent anywhere.

## Scheduled workflows

`.github/workflows/keepalive.yml` (#156) runs `SELECT 1` through the Supabase transaction pooler every Monday and Thursday (and on `workflow_dispatch`), so the free-tier dev project never reaches its inactivity pause. It needs the `KEEPALIVE_DATABASE_URL` Actions secret: the `lineup_app` pooler URL in plain libpq form, `postgresql://lineup_app.<ref>:<password>@<pooler-host>:6543/postgres?sslmode=require`. It is **not** the app's `DATABASE_URL`: `psql` rejects the `+asyncpg` driver suffix and asyncpg-only parameters such as `ssl=` and `prepared_statement_cache_size`. The workflow fails with an error if the secret is missing, and `psql`'s own message stays in the log when the ping fails. It uses no third-party actions. GitHub disables scheduled workflows after 60 days without repo activity and a disabled workflow doesn't fail, so after a long break check the Actions tab and re-enable it (`PLAN.md` §5.3). Once the API is deployed it should also call `/health?db=1`.

## Versions and releases

One repo-wide SemVer version (#17): `[project].version` in `backend/pyproject.toml` and `"version"` in `frontend/package.json` must be equal (`tests/test_versioning.py`); `backend/lineup/version.py` reads the first for the API's OpenAPI `info.version`, so the generated `frontend/src/api/openapi.json` carries it too. To release: `task release:bump -- <patch|minor|major|X.Y.Z>` (edits both files via `scripts/bump_version.py`, then runs `task fe:api`), commit in a PR, merge, then run `.github/workflows/release.yml` (`workflow_dispatch`, from `develop`, or `main` for 1.0.0+). It tags `vX.Y.Z` and publishes a GitHub Release (pre-release below 1.0) with generated notes plus the Alembic revisions added since the previous tag. The bump is a PR because protected branches reject a bot commit that never ran the required checks. Rolling back across a migration needs expand/contract migrations: the deploy's `alembic upgrade head` fails on a revision the old code does not know. `tests/test_versioning.py` also guards the workflow (manual trigger, `contents: write` only, no secrets, pinned action).

## Deploying the dev API

`.github/workflows/deploy-dev.yml` (#8) runs on a push to `develop` that touches `backend/**` (or the workflow itself) and on `workflow_dispatch`: `alembic upgrade head` with the `MIGRATE_DATABASE_URL` secret (table-owner URL through the Supabase **session** pooler, port 5432, `postgresql+asyncpg://…?ssl=require`), then `flyctl deploy --ha=false` from `backend/` with the app-scoped `FLY_API_TOKEN` secret (`fly tokens create deploy -a lineup-dev-lb`), then up to 18 tries (10 s apart) of `GET /health?db=1`. A second job, `smoke` (`needs: deploy`, `if: github.ref == 'refs/heads/develop'`, so never a pull request), starts the API from the checked-out code with `scripts/smoke_auth.py` as the sign-in stand-in and runs `scripts/smoke_live.py` against the dev database as `lineup_app` (secret `SMOKE_DATABASE_URL`, the transaction-pooler URL in `postgresql+asyncpg://…?ssl=require` form, the only secret that job reads). The script is the single definition of the steps, shared with the `supabase-smoke` skill; it always cleans up and sweeps `smoke-<time>` teams older than an hour. A failure only reports (no rollback). Secrets are read only through `env:`; every action in the workflow is pinned to a commit SHA; runs queue (`concurrency`, never cancelled mid-run). The frontend is not part of it: Cloudflare Pages builds `develop` itself. Migrations run before the release, so keep them backwards compatible with the previous code. `tests/test_deploy_workflow.py` guards the workflow; setup and rotation are in `documentation/Fly-Setup.md`.

## Who may commit, push, open and merge

- **With a pre-agreed issue/ticket** (the user named it, or it is already filed and the task refers to it): committing on a branch cut from `develop`, pushing it, opening the PR, watching CI and merging it with a merge commit once the required checks are green are all permitted without asking again. Run the gates in `pr-checklist.md` first, and use `Closes #N` / `Refs #N` as described there. This is the project's value for the generic `create-pr` skill's step 7 ("merge only when asked"): for a pre-agreed issue the agreement counts as the ask, so the skill's default does not apply. Dependabot PRs are not the assistant's own work and still need the user's confirmation (`pr-checklist.md`).
- **Without an agreed issue**, or for anything else outward-facing or hard to reverse (force-push to a shared branch, deleting branches or tags, releases, changing labels, secrets, settings, deploys, merging a PR with a failing check or one that is not yours): ask first.
- **Subagents**: where it is possible and reasonable, hand a task (or its independent parts) to subagents, for example a diff review with `convention-reviewer`, wide searches, or separate pieces of work. Keep small or tightly coupled steps inline. Explore and Plan subagents do not load the rules: put the rule file's path in their prompt.

## Branches and environments

Two environments only (dev + prod, no separate test env), so two long-lived branches:

- **`develop`** — the default branch and integration branch. Feature/fix branches (`feat/<issue>-…`, `fix/…`, `chore/…`) are cut from it and PR'd back into it. A push that changes `backend/` deploys the API to the dev environment (`deploy-dev.yml`, #8). Dependabot PRs target it, and `wiki-sync.yml` publishes `documentation/` from it.
- **`main`** — production. Only changes via a release PR `develop` → `main` (no prod deploy is planned). Version tags and GitHub Releases come from the manual `release.yml` workflow (below). A hotfix branches off `main`, is PR'd into `main`, then `main` is merged back into `develop`.
- Both are protected: changes go through PRs with green `Lint & test`, `E2E (real PDF conversion)`, `Docs updated`, `Migrations (Postgres)` and `Frontend`; no force-pushes or deletions. GitHub can't restrict which branch a PR into `main` comes from, so "only from `develop` (or a hotfix)" is a convention.
- **PRs are merged with a merge commit** (`gh pr merge --merge`), never squash or rebase, so each branch commit and its `#N` reference stays in history, and `git branch -d` works after the merge. Keep branch history clean by amending instead: `git commit --amend` for the last commit, `git commit --fixup=<sha>` + `git rebase --autosquash origin/develop` for an earlier one. After a push, that means `git push --force-with-lease`, on feature branches only. GitHub deletes the remote branch on merge.
