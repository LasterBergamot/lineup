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
task fe:install   # pnpm install --frozen-lockfile in frontend/
task fe:dev       # Vite dev server on :5173, proxies /api to the container from task up
task fe:lint      # ESLint + Prettier check
task fe:format    # Prettier write
task fe:typecheck # tsc --noEmit
task fe:test      # Vitest
task fe:build     # tsc + vite build into frontend/dist
task fe:api       # regenerate frontend/src/api (openapi.json + schema.d.ts) from the backend's OpenAPI spec
task fe:api:check # fail if that generated client is stale (CI runs it)
task fe:check     # lint + test + build + api:check, i.e. the CI Frontend job
task docs:references  # regenerate the dependency block in documentation/References.md
task docs:check   # fail if that block is stale (CI runs it)
```

## Environment variables

Environment variables (`DATABASE_URL`, `ENV`, `CORS_ORIGINS`, `SUPABASE_URL`, `PDF_MAX_CONCURRENT`, `DOCS_ENABLED`, `MAX_BODY_BYTES`, `RATE_LIMIT_GENERATE_PER_USER`, `RATE_LIMIT_GENERATE_PER_IP`, `CLIENT_IP_HEADER`, `SENTRY_DSN`) are documented in `backend/.env.example` — copy it to `backend/.env` (git-ignored; the frontend's public `VITE_*` settings, including `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`, live in the separate `frontend/.env`, see `frontend/.env.example`) to opt into Postgres/Supabase; with no `backend/.env` everything runs on local SQLite.

`ENV=production` also makes startup fail closed (`validate_production_config()`: needs a `postgresql+asyncpg` `DATABASE_URL` with `ssl=require`/`verify-full` and `SUPABASE_URL`) and turns the API docs off, so health checks and scripts must use `GET /health`, not `/docs`. On Fly.io `CLIENT_IP_HEADER=Fly-Client-IP` is already set in `backend/fly.toml`; `DATABASE_URL`, `SUPABASE_URL` and `CORS_ORIGINS` are Fly secrets (`fly secrets set`), never in `fly.toml`. Setup and deploy steps: `documentation/Fly-Setup.md`. The frontend origin (the Cloudflare Pages URL, `documentation/Pages-Setup.md`) has to be in `CORS_ORIGINS`, exact match.

`SENTRY_DSN` (optional env var, unset by default): when set, `app.py` initializes Sentry error monitoring at import time (errors only, no performance tracing). Never set locally/in CI/tests — leaving it unset means `sentry_sdk.init()` is never called and nothing is sent anywhere.

## Scheduled workflows

`.github/workflows/keepalive.yml` (#156) runs `SELECT 1` through the Supabase transaction pooler every Monday and Thursday (and on `workflow_dispatch`), so the free-tier dev project never reaches its inactivity pause. It needs the `KEEPALIVE_DATABASE_URL` Actions secret: the `lineup_app` pooler URL in plain libpq form, `postgresql://lineup_app.<ref>:<password>@<pooler-host>:6543/postgres?sslmode=require`. It is **not** the app's `DATABASE_URL`: `psql` rejects the `+asyncpg` driver suffix and asyncpg-only parameters such as `ssl=` and `prepared_statement_cache_size`. The workflow fails with an error if the secret is missing, and `psql`'s own message stays in the log when the ping fails. It uses no third-party actions. GitHub disables scheduled workflows after 60 days without repo activity and a disabled workflow doesn't fail, so after a long break check the Actions tab and re-enable it (`PLAN.md` §5.3). Once the API is deployed it should also call `/health?db=1`.

## Branches and environments

Two environments only (dev + prod, no separate test env), so two long-lived branches:

- **`develop`** — the default branch and integration branch. Feature/fix branches (`feat/<issue>-…`, `fix/…`, `chore/…`) are cut from it and PR'd back into it. Will deploy to the dev environment once CD exists (#8). Dependabot PRs target it, and `wiki-sync.yml` publishes `documentation/` from it.
- **`main`** — production. Only changes via a release PR `develop` → `main` (later: prod deploy + version tag, #17). A hotfix branches off `main`, is PR'd into `main`, then `main` is merged back into `develop`.
- Both are protected: changes go through PRs with green `Lint & test`, `E2E (real PDF conversion)`, `Docs updated`, `Migrations (Postgres)` and `Frontend`; no force-pushes or deletions. GitHub can't restrict which branch a PR into `main` comes from, so "only from `develop` (or a hotfix)" is a convention.
- **PRs are merged with a merge commit** (`gh pr merge --merge`), never squash or rebase, so each branch commit and its `#N` reference stays in history, and `git branch -d` works after the merge. Keep branch history clean by amending instead: `git commit --amend` for the last commit, `git commit --fixup=<sha>` + `git rebase --autosquash origin/develop` for an earlier one. After a push, that means `git push --force-with-lease`, on feature branches only. GitHub deletes the remote branch on merge.
