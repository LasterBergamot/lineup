# lineup

A tool for generating water polo lineup documents. It takes match details and player information, then fills in a `.docx` template (`backend/resources/rajtlista.docx`) and converts the result to a PDF.

The document can be generated via a REST API, which returns the populated file as a PDF. The API also provides CRUD endpoints for managing teams, players, and saved lineups (persisted in SQLite locally, swappable to Supabase Postgres — currently a dev project; no production deployment exists yet), so a lineup can be built from a saved roster instead of a one-off request payload.

## How it works (start here)

Water polo match officials need a filled-in lineup sheet ("rajtlista") before every game. This project automates that: you give it the match details and the players, it fills a Word template, and hands back a print-ready PDF.

**Document generation** (`POST /lineups`): the request is validated (Pydantic models in `backend/lineup/api/models.py`) and turned into a `WaterPoloLineupDTO`. `WaterPoloLineupCreator` passes it to `DocumentManager`, which fills `backend/resources/rajtlista.docx` using python-docx. For `format=docx` the filled file is returned as is; for `format=pdf` (the default) `PdfConverter` runs LibreOffice in headless mode on it and returns the PDF. LibreOffice only exists inside the container image, which is why the API is run with `task build` + `task up`.

**Persistence layer** (`/teams`, `/players`, `/lineups/saved`): so a lineup can be built from a saved roster instead of retyping everything. Each module (`backend/lineup/teams/`, `backend/lineup/players/`, `backend/lineup/saved_lineups/`) has the same four files: `router.py` (HTTP), `schemas.py` (validation), `service.py` (business rules) and `repository.py` (SQL). Data is stored with SQLAlchemy (async) in a database chosen by the `DATABASE_URL` environment variable: local SQLite by default, Supabase Postgres when configured. Schema changes are managed by Alembic migrations. A saved lineup is a *frozen snapshot* (names copied as text), so deleting a team or player later never alters history.

**Authentication:** every route except `GET /health` and the API docs (off when `ENV=production`) requires a Supabase access token (`Authorization: Bearer <jwt>`, Google sign-in through Supabase Auth). `get_current_user_id()` verifies it against the project's public signing keys and yields the user id; without a valid token the answer is `401`, and rows are only ever read or written for that user. A team is a workspace: its members share its roster and saved lineups; invitation links to add members are the next step. Setup steps: `documentation/Auth-Setup.md`. See the [wiki](https://github.com/LasterBergamot/lineup/wiki) (`documentation/`) for diagrams, the data model and the roadmap; `CLAUDE.md` holds the conventions.

**Repo layout:** all the Python lives in `backend/` and the React web app lives in `frontend/` (see [Frontend](#frontend)); the repo root keeps only shared tooling — `Taskfile.yml`, `compose.yml`, `.github/`, `.claude/`, `documentation/`. Python commands must run with `backend/` as the working directory, because Alembic's config, the `resources/` template paths, pytest's rootdir and the default `./lineup.db` are all cwd-relative. The `task` commands handle that for you (they `cd backend`), so you can run them from the repo root.

**A first tour of the code** (paths relative to `backend/`): `app.py` (wires everything together) → `lineup/api/router.py` (the one-off endpoint) → `lineup/water_polo/` (template filling orchestration) → `lineup/document/` (docx + PDF) → `lineup/db/` (engine and models) → `lineup/teams/` as the example of the persistence layering. `tests/` mirrors the modules one-to-one.

## AI Assistant

This project uses [Claude Code](https://claude.ai/code) as an AI coding assistant. The `CLAUDE.md` file at the root is a short router that Claude Code reads at the start of every session: what the project is, the always-on rules, and a table that says where the detail for each area lives. That detail sits in `.claude/rules/` (one file per area, loaded automatically when Claude reads or edits a matching file) and `.claude/context/` (workflow, pre-PR checklist and skills, read on demand), so a session on the frontend doesn't carry the database notes. `.claude/context/claude-code.md` explains the layout and says which file to update for which kind of change.

Recurring workflows are packaged as skills in `.claude/skills/`. Two of them are lineup-only (`compliance-audit`, `supabase-smoke`). The others, plus the read-only `convention-reviewer` agent in `.claude/agents/`, are generic and come from the owner's private `ai-common` repo through [APM](https://github.com/microsoft/apm) (`apm.yml` pins the version, `apm.lock.yaml` records exactly what was installed). They hold the procedure; lineup's own values (labels, milestones, gates, doc map, audit scope) are in `.claude/context/`. The installed copies are committed, so you need neither APM nor access to `ai-common` to use them; to change one, see `.claude/context/claude-code.md`. Claude picks one up when a request matches its description, or you can call it directly as `/<name>`. Several pin a model in their frontmatter (`model:`), so heavy analysis runs on a stronger model and mechanical steps on a cheaper one, whatever the session default is. The value is always an alias (`opus`, `sonnet`, `haiku`), which Claude Code resolves to the newest model of that tier (currently Claude 5.5), so the skills follow new releases without edits; a test rejects a full model ID:

| Skill | Model | Use it to |
|---|---|---|
| `repo-audit` | opus | audit the whole repo (code, docs/infra/CI, GitHub state) with three parallel explorers, verify the serious findings, then reconcile them with issues and the board — the process behind epics #40–#46 |
| `compliance-audit` | opus | check the repo against GDPR, the Hungarian rules and the OWASP baseline (`requirements.md` next to the skill: what is required, why, where to look), then turn the gaps into issues under epic #92. `quick <issue#\|branch>` is a few-minute check of a single feature, run when its implementation starts and as a `create-pr` gate, so privacy work is planned up front rather than found later |
| `new-issue` | haiku | file or restructure an issue the project's way: Problem/Evidence/Proposal/Acceptance body, `type:`/`area:`/`priority:` labels, milestone, board fields, parent epic, blocked-by links |
| `triage-dependabot` | sonnet | check Dependabot alerts and PRs and classify each PR as blocking/non-blocking (the pre-PR rule in `.claude/context/pr-checklist.md`) |
| `create-pr` | sonnet | get a branch PR-ready (Dependabot triage, lint/test/e2e, docs sync) and open the PR with `Closes`/`Refs` links |
| `supabase-smoke` | haiku | run the live create/generate/invite/delete smoke test against the dev Supabase project after model or engine changes |
| `update-documentation` | sonnet | sync `README.md`, the `.claude/` rule and context files, `CLAUDE.md` and `documentation/` after a change |
| `setup-project` | haiku (high effort) | set up a fresh clone by following `documentation/Setup.md` |

Skills that touch GitHub, git or the database still ask before every state-changing command. `.claude/settings.json` is the shared project config: it lets `task lint`/`task test` run without a prompt and blocks Claude from reading `.env` files (at the root and in `backend/`). Personal overrides go in the git-ignored `.claude/settings.local.json`.

## Documentation & wiki

The `documentation/` folder is the source of truth for the project's [GitHub wiki](https://github.com/LasterBergamot/lineup/wiki) content (current-state and roadmap pages, backend/frontend/cross-cutting, plus two reader-oriented pages: the **Newcomer Guide**, a junior-developer walkthrough of the tools, the request flow and how to make a first change, and **References**, the official docs for every library, tool, service, spec and regulation we use; and the privacy set: **Privacy and Security** (the personal-data inventory), **Privacy Notice**, **Terms and Processor Agreement**, **Compliance Records** and **Breach Runbook**). It's mirrored 1:1 into the wiki by `.github/workflows/wiki-sync.yml` on every push to `develop` that touches `documentation/**`. Edit the files here, not the wiki UI directly — direct wiki edits get overwritten by the next sync.

**Keeping the docs current is part of every change, in the code too.** New or changed public code needs a docstring explaining what it is for and why (`task lint` fails on a missing one; tests and migration revisions are exempt).

**Keeping the docs current is part of every change.** A PR that touches code or config (`backend/lineup/`, `Dockerfile`, `compose.yml`, `Taskfile.yml`, workflows, …) must also update `README.md`, `CLAUDE.md`, a file under `.claude/rules/` or `.claude/context/`, or a page under `documentation/`, or say `No doc impact: <reason>` and carry the `no-docs` label. The `Docs updated` check fails otherwise (run `scripts/check_docs_touched.sh origin/develop HEAD` to try it locally). The dependency tables in `documentation/References.md` are generated: run `task docs:references` after changing a dependency, `Dockerfile` or workflow (`task docs:check` verifies it, and CI runs it).

## Branches

There is one hosted environment (dev/test), and `develop` is its branch. **`develop`** is the default branch: branch off it and open your PR against it (a merged change to `backend/` deploys to dev automatically). **`main`** is the release line and only changes through a release PR from `develop` (or a hotfix). No prod environment is planned. Both are protected and require green CI. PRs are merged with a merge commit (no squash/rebase), so keep your branch's commits tidy with `git commit --amend` / `--fixup` rather than adding "fix" commits. See [Roadmap: Everything Else](https://github.com/LasterBergamot/lineup/wiki/Roadmap:-Everything-Else) for the full model, and `PLAN.md` for the planned dev-preview work.

## Continuous Integration

Four GitHub Actions workflows run automatically on GitHub — no local setup or invocation needed to benefit from them:

- **`.github/workflows/ci.yml`** — on every PR (and push) against `develop` or `main`: a `Frontend` job (ESLint + Prettier, type check, Vitest with 100 % coverage, production build, and a check that the generated API client still matches the backend's OpenAPI spec; it has no path filter, so it reports on every PR), a report-only `Frontend browser tests` job (Playwright at phone and desktop size, `task fe:e2e`), and the backend jobs: lints (`ruff check`, including flake8-bandit's `S` security rules), checks formatting (`ruff format --check`), runs the test suite with 100% coverage enforcement, then builds the container, runs the real PDF-conversion e2e test, and scans the built image for vulnerabilities with Trivy (report-only — findings are visible in the job log and the repo's Security tab, but never fail the build, since the LibreOffice-based image has a CVE surface that can't be fully remediated).
- **`.github/workflows/docs-check.yml`** — on every PR: fails if the diff touches code or config without touching `README.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/context/` or `documentation/` (escape hatch: the `no-docs` label). `ci.yml` additionally runs `task docs:check`, which fails when the generated part of `documentation/References.md` is stale.
- **`.github/workflows/wiki-sync.yml`** — on push to `develop` that touches `documentation/**`: mirrors those files into the GitHub wiki with `scripts/sync_wiki.py` (the page is named after the file's `# Title`, so a new page needs no workflow edit; a removed or renamed file is removed from the wiki; it can also be run by hand from `develop`).
- **`.github/workflows/release.yml`** — by hand only (#17): reads the version from `backend/pyproject.toml` and `frontend/package.json` (they must match), then creates the `vX.Y.Z` tag and a GitHub Release with generated notes and the list of new Alembic migrations. Bump the version first with `task release:bump` in a normal PR; see "Versions and releases" in [Roadmap-Everything-Else](documentation/Roadmap-Everything-Else.md).
- **`.github/workflows/keepalive.yml`** — on Mondays and Thursdays (and by hand): a `SELECT 1` through the Supabase pooler (Actions secret `KEEPALIVE_DATABASE_URL`) so the free-tier dev project is never paused for inactivity. If you've been away for a long time, check the Actions tab: GitHub disables scheduled workflows after 60 days without repo activity.

If you're editing the workflow YAML files themselves, `yamllint` and `actionlint` (see [Prerequisites](#prerequisites)) let you validate them locally before pushing; CI runs both on every PR (`Workflow files` job), and every third-party action must be pinned to a commit SHA (`# vX` comment; `backend/tests/test_ci_workflow.py` fails otherwise).

### Security tooling

- **Dependency updates:** GitHub Dependabot (`.github/dependabot.yml`) opens weekly PRs for outdated Python (`uv`), Docker (base image and `uv` image, pinned by digest) and GitHub Actions dependencies (minor and patch updates grouped per ecosystem, majors separate); security-alert PRs are additionally governed by the repo's "Dependabot security updates" setting.
- **Secret scanning:** GitHub secret scanning + push protection are enabled at the repo level (no code/config in this repo).
- **Static analysis:** `ruff`'s `S` rule category (flake8-bandit) runs as part of `task lint`, and CodeQL (`.github/workflows/codeql.yml`) analyses the Python and TypeScript code on every PR into `develop`/`main`, on every push to them and weekly; findings are in the Security tab.
- **Reporting a vulnerability:** see [`SECURITY.md`](SECURITY.md) (GitHub private vulnerability reporting, not a public issue).
- **Container scanning:** Trivy scans the built image in CI (report-only, see above).
- **Error monitoring:** [Sentry](https://sentry.io) (free Developer tier) — set the `SENTRY_DSN` environment variable in the deployment environment to enable it; errors only, no performance tracing. Unset locally, in CI, and in tests, so nothing is ever sent by default.
- **Logging:** deferred until a real deployment target is chosen — see the "Logging (future)" section of the Roadmap: Everything Else wiki page.

## Prerequisites

Required to install and run the project:

- **Operating System:** Any Linux distribution, preferably **Arch Linux**. On Windows, [Try Omarchy for Windows](https://github.com/omacom/try-omarchy-windows) can be used.
- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — dependency manager
- [Task](https://taskfile.dev/installation/) — task runner
- [Node.js](https://nodejs.org/) (current LTS) and [pnpm](https://pnpm.io/installation) — the web app in `frontend/` and the `task fe:*` targets; the version of pnpm is pinned by `packageManager` in `frontend/package.json`
- [Docker Engine](https://docs.docker.com/engine/) & [Docker Compose](https://docs.docker.com/compose/) — container engine and compose (required for PDF conversion via LibreOffice)
- [GitHub CLI (`gh`)](https://cli.github.com/) — the contribution workflow runs through it: filing issues, opening PRs (`gh pr create`), watching CI (`gh pr checks`, `gh run watch`) and the Dependabot triage. Sign in once with `gh auth login`. The CI and wiki-sync workflows themselves run on GitHub's servers and don't need it

Optional, quality-of-life tools:

- [lazydocker](https://github.com/jesseduffield/lazydocker) — terminal UI for Docker containers (recommended for container management)
- [`yamllint`](https://yamllint.readthedocs.io/) & [`actionlint`](https://github.com/rhysd/actionlint) — only needed if you're modifying `.github/workflows/*.yml`; validate the YAML and GitHub Actions semantics locally before pushing (config: `.yamllint`)

## Installation

The full step-by-step setup, with the expected result of each step, is in
[`documentation/Setup.md`](documentation/Setup.md) (wiki: *Setup*). The short version:

```bash
task doctor    # check the tools above and their versions
task install
```

This runs `uv sync` inside `backend/` and sets up the virtual environment (`backend/.venv`) with all required dependencies.

## Running

Two ways to run things, depending on whether you need PDF output:

```bash
task run      # CLI: fills the template with the sample data in main.py, no server needed
task serve    # local API server with auto-reload; DOCX only (no LibreOffice outside the container)
task build && task up   # full API in a container, with PDF conversion
```

`task run` writes its output to `backend/resources/modified_rajtlista.docx`. With no configuration, the API uses a local SQLite file (`backend/lineup.db`, because `./lineup.db` is resolved from the `backend/` working directory) and creates its tables on startup, so a fresh clone works out of the box.

## Frontend

The web app (React + TypeScript on Vite, styled with Tailwind and the Lineup design system) lives in `frontend/`. It is a single-page app that talks to the API over HTTP; nothing in the backend changes for it to run.

```bash
task fe:install   # pnpm install (exact versions from frontend/pnpm-lock.yaml)
task up           # the API container the app talks to, on :8000
task fe:dev       # Vite dev server on http://localhost:5173
```

In dev the browser calls the same-origin `/api/...` and Vite proxies it to the container (`VITE_DEV_API_TARGET`, default `http://localhost:8000`), so no CORS setup is needed locally. Deployed builds set `VITE_API_URL` instead (the dev site on Cloudflare Pages is set up as described in the [Pages Setup](https://github.com/LasterBergamot/lineup/wiki/Pages-Setup) wiki page; `frontend/public/_headers` holds its security headers); copy `frontend/.env.example` to `frontend/.env` to change any of these (everything `VITE_*` ends up in the public bundle, so never put a secret there).

The API client in `frontend/src/api/` is **generated** from the backend's OpenAPI spec, so request and response types can't drift from the API. After changing a backend endpoint or schema run `task fe:api` and commit the result; `task fe:api:check` (run by CI) fails when it is stale. `task fe:check` runs everything the CI `Frontend` job does.

The whole app sits behind **Google sign-in**: the sign-in page (`/sign-in`) hands over to Supabase Auth (`@supabase/supabase-js`, used for sign-in only, PKCE flow), every API call then carries the access token, and the API answers `401` without one. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env` (the *publishable* key; the app refuses a secret key because `VITE_*` values are public) and do the one-off dashboard setup from `documentation/Auth-Setup.md`; until then the sign-in page says that sign-in is not configured. A signed-in user who is in no team yet is asked to create one or to paste an invite link; after that the shell shows the current team and a sign-out button. The **Team** page (`/members`) lists the members (as "You" and "Member N", the API stores no names) and lets an owner remove a member, hand the team over, and create, copy or share and revoke invite links (2 hours, 24 hours or 3 days); anyone can leave. An invite link opens `/join/<code>`, which shows what you are joining before you sign in, survives the Google round trip and joins only when you press the button.

The first screen is the **lineup creator** (`/`): pick the players from the roster (or type them in), choose the opponent from the directory, your recent opponents or free text, **preview** the sheet as a PDF (rendered in the browser with pdf.js) and **save** it, then download it as PDF or DOCX. "Quick sheet" is the one-off form: it calls `POST /lineups` and stores nothing. Both validate with the same limits as the API and shows the API's own field errors if one slips through. The **Roster** page (`/roster`) manages the current team: every member can add, edit and delete players (name and NSSZ number only), owners can rename the team and choose whether its name is listed in the opponent directory, and a search box browses the listed teams (names only). For PDFs run the API with `task build && task up` (LibreOffice is only in the container), otherwise only DOCX works.

**On a phone** the app has a top bar and a bottom navigation, 44 px tap targets on touch screens, 16 px text fields (so iOS does not zoom in on focus) and a web-app manifest, so it can be added to the home screen and opens full-screen (there is no service worker: nothing is cached for offline use). `task fe:e2e` drives the production build in Chromium at a phone and a desktop size with the network mocked, checks that the main screens, the sign-in page, the invite page and the 404 page do not scroll sideways and runs axe accessibility checks (no serious or critical violations, plus WCAG 2.5.3 label-in-name) in English and Hungarian; CI runs it as a report-only job.

The UI is **Hungarian by default** and English is selectable (`react-i18next`; the HU/EN switch is in the account panel and on the sign-in page). The texts live in `frontend/src/i18n/locales/hu.json` and `en.json`; a component never contains a literal string (ESLint's `i18next/no-literal-string` fails `task fe:lint`) and a test fails when the two files differ in their keys. The choice is kept in localStorage under `lineup-lang` (the only thing stored besides the sign-in session and the theme) and `<html lang>` follows it. The `.docx` template, the API and the sentences the API returns for a rejected field stay as they are, so those few sentences appear in English.

The hosted API is expected to sleep when idle, so the app asks `GET /health` as soon as it loads and, if the answer takes more than ~1.5 s, shows a non-blocking "server is starting up" banner (set `VITE_COLD_START_NOTICE=false` to turn it off on always-on hosting). Data regions show skeletons meanwhile, and failed requests are retried with backoff only when the failure looks temporary. See *Current State: Frontend* on the wiki.

## Environment variables

Configuration is through environment variables, all optional. `backend/.env.example` documents each one; copy it to `backend/.env` (git-ignored, never commit it) and uncomment what you need.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lineup.db` (in the container: `…:////data/lineup.db`, on a Compose volume) | Database to use. SQLite locally, or a Supabase Postgres URL (see below) |
| `ENV` | unset | Set to `production` to skip the automatic table creation on startup because Alembic owns the schema. Set it for **any** real Postgres (dev or prod), despite the name. It also makes startup **fail closed**: the app refuses to start unless `DATABASE_URL` is a `postgresql+asyncpg` URL with `ssl=require` (or `verify-full`, preferred) and `SUPABASE_URL` is set, and it turns the API docs off |
| `CORS_ORIGINS` | unset | Comma-separated browser origins allowed to call the API (e.g. `http://localhost:5173` for the Vite dev server). Unset = no CORS headers. `*` is refused at startup |
| `APP_BASE_URL` | `http://localhost:5173` | The web app's origin: team invite links are built as `<APP_BASE_URL>/join/<code>`. `fly.toml` sets it to the Cloudflare Pages URL |
| `DOCS_ENABLED` | `true` | Serve `/docs`, `/redoc` and `/openapi.json`. Always off when `ENV=production`, whatever this says. The frontend's client is generated offline (`task fe:api`), so it never needs the route |
| `MAX_BODY_BYTES` | `262144` | Largest request body (256 KiB). Bigger ones get `413`, checked on `Content-Length` and again while streaming |
| `RATE_LIMIT_GENERATE_PER_USER` | `10` | Document generations per minute and signed-in user (`POST /lineups`, `POST /lineups/saved/{id}/generate` share it). Over the limit: `429` + `Retry-After` |
| `RATE_LIMIT_GENERATE_PER_IP` | `30` | The same, per client IP; checked before sign-in so it also throttles bad-token floods |
| `CLIENT_IP_HEADER` | unset | Header that carries the real client IP, for the per-IP limit (Fly.io: `Fly-Client-IP`). Only set it when the proxy overwrites that header; unset = the socket peer's address (behind a proxy that is the proxy, so everyone shares one bucket) |
| `SUPABASE_URL` | unset | Project URL (`https://<ref>.supabase.co`). The API derives the token issuer and the signing-key (JWKS) address from it. Unset = every protected route answers `503` (fail closed). Must be `https` (plain `http` only for localhost). See `documentation/Auth-Setup.md` (wiki: *Auth Setup*) |
| `PDF_MAX_CONCURRENT` | `2` | How many LibreOffice conversions may run at once. Each is a separate process of a few hundred MB; extra requests wait up to 10 s, then get `503` with `Retry-After` |
| `SENTRY_DSN` | unset | Enables Sentry error reporting. Leave unset locally, in CI and in tests |

`task up` (Docker Compose, via `env_file: backend/.env` in `compose.yml`) and `task serve` both load `backend/.env` automatically; it lives in `backend/` beside `backend/.env.example` so it is kept out of the image by `backend/.dockerignore`. `task migrate` and `task migrate-new` deliberately do **not**: they target local SQLite unless you pass `DATABASE_URL` for that one run, so a migration never hits Supabase by accident.

**Switching databases:** `task db:postgres` / `task db:sqlite` flip `backend/.env` between the Supabase pooler and local SQLite (it uncomments or comments the pooler `DATABASE_URL` and adds or removes `ENV=production`), and `task db:status` shows which one is active and the `ENV` it runs with, warning when the two disagree (a Postgres URL without `ENV=production` skips the fail-closed startup checks). The logic lives in `scripts/db_env.py`. Restart `task serve` or run `task up` afterwards to apply the change. `db:postgres` needs a filled-in pooler URL (port 6543) already in `backend/.env`; it never invents one.

### Using the Supabase dev database

The dev environment can run against a hosted Postgres on [Supabase](https://supabase.com) (project `lineup-dev`). This only replaces the database; authentication is not wired up yet.

1. Put the **transaction pooler** URL (port 6543, with `?ssl=require`) in `backend/.env` as `DATABASE_URL`, and set `ENV=production`. Exact URL formats are in `backend/.env.example`. `ENV=production` is the right value for the dev database too: it means "fail closed and no API docs", not "this is the prod deployment". Tables are never created by the app on Postgres, only by `task migrate:supabase`. The app uses the pooler rather than the direct connection because the direct host is IPv6-only and, with one fresh connection per request, is slower and burns Postgres's limited connection slots; the direct connection is only needed for the one-off migration in step 2. Tip: `chmod 600 backend/.env` keeps other users on your machine from reading it.
2. Put the **owner's direct** connection string (port 5432; the pooler can't run migrations, and on IPv4-only networks use the session-mode pooler instead) in a separate git-ignored file, `backend/.env.migrate`, as `MIGRATE_DATABASE_URL` (`chmod 600`). It is kept out of `.env` on purpose: Compose and `task serve` load `.env` into the API's environment, and the API must never hold the owner's password. Then run `task migrate:supabase`. This creates the tables **and** switches on Row Level Security with a least-privilege `lineup_app` role (see *Current State: Backend* on the wiki).
3. Run `task db:create-app-role`: it gives `lineup_app` a generated password and rewrites the pooler `DATABASE_URL` in `backend/.env` to that role (nothing is printed). The API then connects as `lineup_app`, not as the table-owning `postgres` role. It generates a **new** password on every run, so it asks you to type `yes` first (`task db:create-app-role -- --yes` skips the question for scripts); a second run invalidates the old password, and the deployed API's Fly secret `DATABASE_URL` and the `KEEPALIVE_DATABASE_URL` Actions secret then have to be updated (`documentation/Fly-Setup.md`).
4. Start the app (`task up` or `task serve`; both read `backend/.env`).

**Switching back to local SQLite:** run `task db:sqlite` and restart (or comment out `DATABASE_URL` and remove `ENV` in `backend/.env` by hand). Nothing else changes: the task only comments Postgres URLs out (whatever their port), it never deletes them, and `task db:postgres` uncomments it again.

**If the credentials are lost:** the database password can be reset at any time in the Supabase dashboard (Project Settings → Database → *Reset database password*) without losing data; update your `backend/.env`. API keys and the JWT secret are always viewable and rotatable in Project Settings. The only unrecoverable situation is losing access to the Supabase account itself, so keep the account recovery e-mail and 2FA backup codes safe and consider adding a second owner to the organization.

**Changing the schema later:** edit `backend/lineup/db/models.py`, run `task migrate-new -- -m "description"` (against local SQLite), review the generated file in `backend/alembic/versions/`, then `task migrate` (and `task migrate:supabase` to update Supabase). `task migrate-check` (also run by CI) fails if the models and the migrations disagree. Moving to a different database or cloud provider someday is covered in the wiki's *Current State: Backend* page.

## API

The API runs inside a container so that LibreOffice is available for PDF conversion. The
image also bundles the libre, metric-compatible fonts (Carlito for Calibri, etc.) that the
template relies on, so the generated PDF matches the source `.docx` layout.

```bash
task build
task up
```

Starts the API server at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs` (they are switched off with `ENV=production` or `DOCS_ENABLED=false`; `GET /health` is the probe that is always there). You can monitor and manage containers using [lazydocker](https://github.com/jesseduffield/lazydocker).

### `GET /health`

Health probe for the container, deploys and uptime checks. `GET /health` answers `200 {"status":"ok"}` without touching the database (liveness). `GET /health?db=1` also runs `SELECT 1` (readiness) and answers `503 {"status":"unavailable"}` when the database can't be reached; the body never contains driver error text.

### `POST /lineups`

Generates a lineup document from the provided data. Requires `Authorization: Bearer <Supabase access token>`. Every text field has a maximum length (match, name and staff fields 200, team name 120, division 100, date 50, NSSZ number 50 characters); longer values are rejected with `422`.

**Query parameters:**

| Parameter | Values        | Default | Description                         |
|-----------|---------------|---------|-------------------------------------|
| `format`  | `pdf`, `docx` | `pdf`   | Output format of the generated file |

**Request body:**

```json
{
  "match": "SZVTK - Csongrád",
  "division": "OB II.",
  "team_name": "SZVTK",
  "cap": "Fehér",
  "date": "2024. 12. 21.",
  "coach": "...",
  "doctor": "...",
  "assistant_coach": "...",
  "team_leader": "...",
  "ball_thrower": "...",
  "players": [
    { "cap_number": 1, "name": "...", "nssz_number": "..." }
  ]
}
```

`cap` must be `"Fehér"` or `"Kék"`. `players` accepts 1–15 entries; cap numbers must be unique integers between 1 and 15.

**Response:**

Returns the lineup file with a `Content-Disposition: attachment` header containing the filename. The content type depends on the requested format.

```
# PDF (default)
Content-Type: application/pdf
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024-12-21.pdf"; filename*=UTF-8''rajtlista_SZVTK_2024-12-21.pdf

# DOCX
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024-12-21.docx"; filename*=UTF-8''rajtlista_SZVTK_2024-12-21.docx
```

The header carries the name twice. HTTP headers are latin-1, so a team name with `ő`/`ű` can't go into plain `filename="..."`. The real UTF-8 name goes in `filename*` (RFC 6266), which browsers prefer; `filename` is an accent-stripped ASCII fallback (`Szőreg` → `Szoreg`). Spaces in the team name become `_` and the date's dots and spaces become `-` (`2024. 12. 21.` → `2024-12-21`), so the name never has spaces or a `..`; the document itself prints the date as typed.

**Auth and limits:** `POST /lineups` needs a signed-in user like every data route (`401` otherwise). Both generate endpoints are rate limited per user and per IP (`429` with `Retry-After`), and request bodies over 256 KiB get `413`. Every response carries the security headers (HSTS, `nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY` / CSP `frame-ancestors 'none'`) and `Cache-Control: no-store`, because all payloads are personal data or generated documents.

**Errors:** `401` without a valid token, `413` for an oversized body, `422` for invalid input, `429` when the rate limit is exceeded, `503` (with `Retry-After`) if every PDF conversion slot stays busy for 10 s (see `PDF_MAX_CONCURRENT`), `504` if LibreOffice doesn't finish the PDF conversion within 120 s (the whole LibreOffice process group is then killed), `500` for any other rendering failure. The same rendering, headers and errors apply to `POST /lineups/saved/{id}/generate`. Conversion runs in a worker thread, so a slow PDF never blocks the other endpoints.

### Teams, Players & Saved Lineups

Backed by a SQLite database (in-memory for tests, file-backed at `backend/lineup.db` for local dev via `task serve`, swappable to Supabase Postgres via `DATABASE_URL` — see [Environment variables](#environment-variables)). Text input is checked everywhere the same way: values are trimmed, must not be empty or whitespace-only, and must not contain control characters (tabs, newlines, NUL…), all with `422`. Optional fields treat a blank value as "not provided". Lists come back in a stable order (teams by name, players and saved lineups by creation time, with the id as tie-breaker) so pages never repeat or skip rows, and a saved lineup's players are always sorted by cap number. All list endpoints are paginated: `?limit=20&offset=0` (`limit` is 1–200; there is no "return everything" mode, page with `offset`), in the envelope `{ "items": [...], "total": ..., "limit": ..., "offset": ... }`.

| Method | Path | Description |
|--------|------|--------------|
| `GET`/`POST` | `/teams` | List the teams you belong to (each with your `role`) / create a team (you become its owner) |
| `GET` | `/teams/pool?search=&limit=` | Search the opponent directory (teams that chose to be listed; only `id` + `name` are exposed) — plain list, not paginated. `search` is a literal, case-insensitive substring (`%` and `_` are not wildcards), max 120 characters |
| `GET` | `/teams/{id}/opponents/recent?limit=` | Opponent names used in this team's saved lineups, newest first (for the opponent combobox) |
| `GET`/`POST` | `/teams/{id}/invitations` | Owner-only: list the invite links that still work (no codes) / create one (`{"expires_in_hours": 2 \| 24 \| 72}`, default 24). The response carries `code` and `url` **once**; only a hash is stored |
| `DELETE` | `/teams/{id}/invitations/{invitation_id}` | Owner-only: revoke a link (204) |
| `GET` | `/invitations/{code}` | **Public**, rate limited: team name, inviter's display name and expiry of a link. **404** unknown, **410** expired or revoked |
| `POST` | `/invitations/{code}/accept` | Join the team behind the link as a member (returns the team with your role). Safe to repeat; **404**/**410** as above |
| `GET` | `/teams/{id}/members` | Members of the team: user id, role, join date, `is_you` (any member) |
| `DELETE` | `/teams/{id}/members/{member_id}` | Owner removes a member, or a member removes themselves (leave). **409** for the last owner |
| `POST` | `/teams/{id}/transfer-ownership` | Owner-only: `{"user_id"}` becomes the owner, you become a member |
| `GET`/`PUT`/`DELETE` | `/teams/{id}` | Get / rename and list-or-unlist (`is_public`) / delete a team. Update and delete are owner-only (**403** for other members). Delete returns **409** while the team has players or saved lineups |
| `GET`/`POST` | `/players` | List the players of your teams (optionally `?team_id=`) / add a player to a team's roster (`team_id` is required and must be a team you belong to, else **404** `Team not found`) |
| `GET`/`PUT`/`DELETE` | `/players/{id}` | Get / update (moving to a team you're not in is a **404**) / delete a player. Delete is always safe (204) — saved lineups are frozen snapshots, so deleting a player never breaks them |
| `GET`/`POST` | `/lineups/saved` | List the saved lineups of your teams (optionally `?team_id=` or `?source_team_id=`) / create one in a team's workspace (`team_id`, required) |
| `GET`/`DELETE` | `/lineups/saved/{id}` | Get / delete a saved lineup |
| `POST` | `/lineups/saved/{id}/generate?format=pdf\|docx` | Generate a PDF/DOCX from a previously saved lineup |

A saved lineup freezes team/opponent names and each player's name/NSSZ number as text at creation time. Team, opponent, and each player can be specified either by referencing an existing record (`source_team_id`, `source_opponent_id`, `source_player_id` — the current name/NSSZ is copied in) or by free text (`team_name`, `opponent_name`, player `name`/`nssz_number`); **exactly one** of the two must be given per field (sending both is a `422`, so it is never ambiguous which value wins). The same NSSZ number can't appear twice in one lineup (`422`), on either endpoint. Once saved, deleting the source team or player has no effect on the lineup. Everything is looked up **as you**: ids of teams or players outside your teams are a `404` (an opponent may also be a team listed in the directory).

```json
POST /lineups/saved
{
  "team_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "source_team_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "opponent_name": "Csongrád VVSE",
  "division": "OB II.",
  "cap": "Fehér",
  "date": "2024. 12. 21.",
  "coach": "Török András",
  "players": [
    { "source_player_id": "9a12bcde-...", "cap_number": 1 }
  ]
}
```

## Available tasks

| Task            | Description                                                     |
|-----------------|-----------------------------------------------------------------|
| `task install`  | Install dependencies via `uv sync`                              |
| `task doctor`   | Check the required tools and their minimum versions (`scripts/doctor.sh`) |
| `task run`      | Run the CLI application                                         |
| `task serve`    | Start the API server locally (DOCX only; loads `backend/.env`; creates the SQLite tables on startup via `AUTO_CREATE_SCHEMA=1`) |
| `task db:status` | Show whether `backend/.env` selects SQLite or the Supabase pooler, and warn if `ENV` doesn't match |
| `task db:query -- "SQL"` | Run one read-only statement with `psql` as the app role (`--owner` uses `backend/.env.migrate`); needs the PostgreSQL client tools; the URL is never printed |
| `task db:postgres` | Switch `backend/.env` to the Supabase pooler (`DATABASE_URL` + `ENV=production`) |
| `task db:sqlite` | Switch `backend/.env` back to local SQLite                             |
| `task test`     | Run tests with coverage (100%)                                  |
| `task test-e2e` | Build+run the container and verify real PDF conversion fidelity (makes a throw-away signing key so the test can sign in; runs as its own Compose project `lineup-e2e` on host port 8001, so a running `task up` is left alone) |
| `task lint`     | Lint the codebase with ruff                                     |
| `task format`   | Format the codebase with ruff                                   |
| `task build`    | Build the container image                                       |
| `task rebuild`  | Force a fresh container image build (no cache)                  |
| `task up`       | Start the API in a container (detached)                         |
| `task down`     | Stop the container (its SQLite data stays on the `lineup-data` volume; `docker compose down -v` deletes it) |
| `task migrate`  | Apply Alembic migrations (`upgrade head`)                        |
| `task migrate-new -- -m "description"` | Autogenerate a new Alembic migration          |
| `task migrate-down` | Roll back one migration step                                 |
| `task migrate-check` | Apply all migrations to a throwaway SQLite file and fail on model/migration drift |
| `task migrate:supabase` | Apply migrations to Supabase using `MIGRATE_DATABASE_URL` from `backend/.env.migrate` |
| `task db:create-app-role` | Set or rotate the `lineup_app` login (asks for a typed `yes` first; generated password, written to `backend/.env`, never printed) |
| `task fe:install` | Install the frontend dependencies with pnpm (frozen lockfile)   |
| `task fe:dev`   | Start the Vite dev server on :5173 (proxies `/api` to the container) |
| `task fe:lint`  | ESLint and Prettier check for the frontend                      |
| `task fe:format` | Format the frontend with Prettier                              |
| `task fe:typecheck` | TypeScript type check                                       |
| `task fe:test`  | Run the frontend unit tests (Vitest)                            |
| `task fe:coverage` | Run them with a coverage report; fails below 100 % (CI runs it)  |
| `task fe:e2e`   | Browser tests (Playwright) at phone and desktop size; set `LINEUP_CHROMIUM=/usr/bin/chromium` to use an installed browser, or run `task fe:e2e:install` once |
| `task fe:build` | Type-check and build the production bundle into `frontend/dist` |
| `task fe:api`   | Regenerate the typed API client from the backend's OpenAPI spec |
| `task fe:api:check` | Fail if the committed API client is stale (CI runs it)      |
| `task fe:check` | Everything the CI `Frontend` job runs                           |
| `task release:bump -- minor` | Bump the version in `backend/pyproject.toml` and `frontend/package.json` (`patch`, `minor`, `major` or `X.Y.Z`) and regenerate the API client |
| `task docs:references` | Regenerate the dependency block in `documentation/References.md` |
| `task docs:check` | Fail if that block is stale (CI runs it)                       |

## Project structure

```
lineup/
├── Taskfile.yml                     # Task runner commands (Python tasks run with dir: backend)
├── compose.yml                      # Docker Compose configuration (reads optional backend/.env)
├── compose.e2e.yml                  # Extra Compose file for `task test-e2e`: lets the container trust a throw-away test signing key, moves it to port 8001 and drops `backend/.env`
├── documentation/                   # Source of the GitHub wiki (mirrored by CI; incl. Setup.md, Newcomer-Guide.md, References.md, Auth-Setup.md, Fly-Setup.md, Pages-Setup.md, Supabase-Admin-Guide.md)
├── scripts/                         # Repo tooling: doctor.sh (`task doctor`: tool check), check_docs_touched.sh (docs gate), docs_references.py (References generator), sync_wiki.py (documentation/ to wiki mirror), dump_openapi.py (spec for the FE client), e2e_keys.py (throw-away signing key for `task test-e2e`), smoke_auth.py (fake Supabase Auth for the smoke test), db_env.py and db_query.py (`task db:*`), smoke_live.py (the live smoke test, shared by the supabase-smoke skill and the post-deploy CI job)
├── SECURITY.md                      # Security policy: how to report a vulnerability privately
├── .github/                         # CI (ci.yml, codeql.yml, docs-check.yml, wiki-sync.yml), PR template, ISSUE_TEMPLATE/ (bug, feature, chore forms), dependabot.yml
├── .claude/                         # settings.json; skills/ and agents/ (generic ones installed from ai-common); rules/ (path-scoped, auto-loaded); context/ (read on demand)
├── apm.yml  apm.lock.yaml           # APM: pins the ai-common version the generic skills come from (apm_modules/ is git-ignored)
├── PLAN.md  PLAN-ui-redesign.md     # Working plans: the dev preview; porting the new UI design system into frontend/ (delete when done)
├── CLAUDE.md  README.md             # Assistant router (detail in .claude/rules + .claude/context); this file
├── frontend/                        # React + TypeScript + Vite web app (pnpm)
│   ├── DESIGN.md                    # Design system spec (tokens, shapes, wordmark)
│   ├── package.json  pnpm-lock.yaml # Dependencies and scripts (packageManager pins pnpm)
│   ├── eslint.config.js  tsconfig.json  index.html
│   ├── playwright.config.ts  tsconfig.e2e.json  # Browser tests (task fe:e2e)
│   ├── e2e/                         # Playwright specs (*.e2e.ts) + fixtures.ts (mocked API and Supabase)
│   ├── scripts/make-icons.mjs       # Renders the PNG icons in public/ (pnpm icons)
│   ├── vite.config.ts               # Vite + Tailwind + Vitest config, /api dev proxy
│   ├── .env.example                 # VITE_* settings (public values only)
│   ├── public/                      # Static files (favicon, theme-init.js, manifest.webmanifest, icons, _headers)
│   └── src/
│       ├── main.tsx  app.tsx        # Entry point, providers and route table
│       ├── index.css                # Tailwind + design tokens (light/dark)
│       ├── api/                     # client.ts, errors.ts, query-client.ts, auth-middleware.ts + generated openapi.json / schema.d.ts
│       ├── auth/                    # Google sign-in: config.ts (env check), supabase.ts (sign-in-only client), provider/context, require-auth, return-path, events
│       ├── backend-status/          # Cold-start handling: /health polling, provider, banner
│       ├── components/              # app-shell (sidebar / bottom nav), account-panel (team + sign out), language-switch (HU/EN), brand, theme-toggle, nav-items, query-boundary, confirm-button (two-step confirm), ui/ (shadcn-style)
│       ├── features/lineup/         # One-off lineup form ("Quick sheet"): schema.ts (Zod), generate.ts, download.ts, lineup-form.tsx
│       ├── features/creator/        # Lineup creator: schema.ts (Zod), resolve.ts (form values -> requests), api.ts, lineup-creator.tsx, opponent/ (combobox over directory + recent opponents)
│       ├── features/preview/        # PDF preview: pdfjs.ts (lazy loader, bundled worker), pdf-viewer.tsx, preview-panel.tsx (side panel / full-screen sheet)
│       ├── features/teams/          # Teams of the signed-in user: api.ts (list/create/update), provider/context, team-gate, onboarding, create-team-form, team-settings-card (owners), role.ts
│       ├── features/players/        # A team's roster: api.ts (list/create/update/delete), schema.ts (Zod), player-form, players-card
│       ├── features/directory/      # Opponent directory search: api.ts (GET /teams/pool), directory-card (names only)
│       ├── features/members/        # A team's people: api.ts (list/remove/leave/hand over), members-list
│       ├── features/invitations/    # Invite links: api.ts, code.ts (parse a pasted link), invite-panel (owner tools), invite-link-form (onboarding)
│       ├── i18n/                    # react-i18next setup (index.ts), error-key.ts (translated form errors), locales/hu.json + en.json
│       ├── pages/                   # One file per route
│       ├── lib/                     # utils.ts (cn), theme.ts, use-after-delay.ts, use-debounced-value.ts, clean-text.ts (shared Zod text rule), format-date.ts
│       └── test/                    # setup.ts (Vitest + Testing Library), auth.tsx (fake auth client, renderApp)
└── backend/                         # All Python; the working directory for Python commands
    ├── main.py                          # CLI entry point
    ├── app.py                           # FastAPI application entry point
    ├── pyproject.toml  uv.lock          # Dependencies, ruff/pytest/coverage config
    ├── Dockerfile                       # Container image definition
    ├── fly.toml                         # Fly.io app config for dev (scale to zero, EU region; no secrets)
    ├── .dockerignore                    # Keeps secrets/tests out of the image (build context is backend/)
    ├── .env.example                     # Documents the env vars; copy to git-ignored backend/.env
    ├── alembic.ini                      # Alembic configuration
    ├── alembic/
    │   ├── env.py                       # Async migration environment
    │   └── versions/
    │       ├── 35ce55ceabf4_initial_schema.py  # teams/players/saved_lineups/lineup_player_snapshots
    │       ├── 8b1f3c2d9a47_rls_and_least_privilege_role.py  # Postgres-only RLS + lineup_app role
    │       ├── c4e7a1b2d905_pin_rls_function_search_path.py  # Postgres-only: pinned search_path on the trigger function
    │       ├── a3d5f7c91e26_team_members_invitations_owner_not_null.py  # team_members/team_invitations; owner columns NOT NULL
    │       ├── e5b8c2d41f70_team_as_workspace.py  # teams are workspaces: created_by, required team_id on players/saved_lineups
    │       ├── b7d2e9a41c53_invitation_inviter_name.py  # team_invitations.invited_by_name
    │       ├── d9a4c6e81b32_snapshot_cap_unique_and_source_indexes.py  # unique cap per lineup + FK indexes
    │       └── f2c8a5d7e931_timestamptz_and_server_defaults.py  # Postgres: timestamptz columns + server defaults
    ├── docker/
    │   └── fontconfig/
    │       └── 99-calibri-carlito.conf  # Calibri → Carlito font mapping (copied into image)
    ├── resources/
    │   └── rajtlista.docx               # Input document template
    ├── lineup/
    │   ├── api/
    │   │   ├── models.py                # Pydantic request models
    │   │   ├── file_response.py         # Shared rendering + download response for both generate endpoints
    │   │   └── router.py                # POST /lineups endpoint
    │   ├── document/
    │   │   ├── document_manager.py      # .docx read/write logic
    │   │   └── pdf_converter.py         # docx → PDF via LibreOffice
    │   ├── water_polo/
    │   │   ├── water_polo_lineup_creator.py  # Orchestrates document generation
    │   │   └── water_polo_lineup_dto.py      # Data model and builders
    │   ├── db/
    │   │   ├── base.py                  # DeclarativeBase
    │   │   ├── engine.py                # DB engine (SQLite foreign keys), get_session() dependency
    │   │   ├── connection_settings.py   # URL-only settings: pooler-safe engine kwargs, AUTO_CREATE_SCHEMA rule (Alembic imports it)
    │   │   ├── types.py                 # UtcDateTime: timestamptz that is always aware UTC
    │   │   ├── app_role.py              # `task db:create-app-role`: lineup_app password + .env rewrite
    │   │   ├── urls.py                  # to_asyncpg_url(): plain postgresql:// -> postgresql+asyncpg://
    │   │   └── models.py                # Team, Player, SavedLineup, LineupPlayerSnapshot
    │   ├── auth/
    │   │   ├── dependencies.py          # get_current_user_id(): verifies the Bearer JWT, 401/503 otherwise; get_current_display_name()
    │   │   └── tokens.py                # JWT verification + JWKS cache; display_name_from_token()
    │   ├── security/
    │   │   ├── headers.py               # Security headers + Cache-Control: no-store on every response (ASGI middleware)
    │   │   ├── body_limit.py            # Request body size cap (MAX_BODY_BYTES), 413
    │   │   ├── rate_limit.py            # In-memory sliding-window limiter (generate and invitation endpoints), 429
    │   │   └── config.py                # DOCS_ENABLED parsing + fail-closed ENV=production startup check
    │   ├── common/
    │   │   ├── types.py                 # CleanStr* / OptionalCleanStr* input types
    │   │   └── errors.py                # IntegrityError -> 409 handler
    │   ├── health/
    │   │   └── router.py                # GET /health, /health?db=1
    │   ├── teams/                       # schemas / repository / service / router (incl. members, ownership transfer)
    │   ├── invitations/                 # schemas / repository / service / router (invite links: create, list, revoke, preview, accept)
    │   ├── players/                     # schemas / repository / service / router
    │   └── saved_lineups/                # schemas / repository / service / router
    ├── tests/
    │   ├── resources/
    │   │   ├── expected_rajtlista.docx  # Test fixture
    │   │   └── expected-rajtlista.pdf   # Reference render for the e2e fidelity test
    │   ├── conftest.py                  # Shared fixtures
    │   ├── test_api.py                  # API endpoint tests
    │   ├── test_app.py                  # Sentry init unit tests
    │   ├── test_document_manager.py     # DocumentManager unit tests
    │   ├── test_pdf_converter.py        # PdfConverter unit tests
    │   ├── test_pdf_conversion_e2e.py   # Real-conversion fidelity tests (container)
    │   ├── test_water_polo_lineup_creator.py  # Creator unit tests
    │   ├── test_water_polo_lineup_dto.py      # DTO and builder unit tests
    │   ├── test_auth_dependencies.py    # JWT verification, JWKS cache, 401 on every protected route
    │   ├── test_tenant_isolation.py     # Two users can't reach each other's rows (404); teammates share theirs
    │   ├── helpers.py                   # ensure_team()/create_player(): most API tests need a team first
    │   ├── test_security.py             # Security headers, body cap, rate limits (429), docs exposure, production config check
    │   ├── test_health.py               # /health liveness + readiness
    │   ├── test_db_urls.py              # to_asyncpg_url()
    │   ├── test_app_role.py             # lineup.db.app_role (password + .env rewrite, fake engine)
    │   ├── test_postgres_migrations.py  # RLS / roles / grants on a real Postgres (skipped without POSTGRES_TEST_URL)
    │   ├── test_migrations.py           # Data migrations on a throw-away SQLite file
    │   ├── test_db_env.py               # scripts/db_env.py (task db:status / db:sqlite / db:postgres on temp .env files)
    │   ├── test_db_query.py             # scripts/db_query.py (task db:query: libpq variables, read-only wrapper, no URL leaks)
    │   ├── test_smoke_auth.py           # scripts/smoke_auth.py tokens are accepted by the real verifier
    │   ├── test_smoke_live.py           # scripts/smoke_live.py run against the real app: steps, failure, cleanup, sweep
    │   ├── test_input_hardening.py      # Control chars/blanks, unknown team_id, source-or-text, duplicate NSSZ, ordering
    │   ├── test_docs_tooling.py         # scripts/ (References generator, docs gate), wiki page naming and sync (`scripts/sync_wiki.py`), Claude context guards
    │   ├── test_db_engine.py            # DB engine unit tests (SQLite pragma gate)
    │   ├── test_connection_settings.py  # pooler-safe engine kwargs, AUTO_CREATE_SCHEMA rule
    │   ├── test_db_models.py            # ORM model unit tests
    │   ├── test_teams.py                # Teams API + repository tests
    │   ├── test_players.py              # Players API + repository tests
    │   └── test_saved_lineups.py        # Saved lineups API + repository tests
```

## Customizing the lineup

Edit `backend/main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloLineupDTO` and `Player` classes both use the builder pattern.
