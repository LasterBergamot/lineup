# Current State: Everything Else

Cross-cutting concerns: dev workflow, containerization, testing, and conventions that apply
across the backend regardless of which module you're touching.

## Repository layout

The repo is split so each side can be built, tested and deployed on its own: **`backend/`**
holds all the Python (API, Alembic migrations, tests, `Dockerfile`, `pyproject.toml`, the
`.docx` template), and **`frontend/`** holds the web app (React + TypeScript on Vite, pnpm; see [[Current State: Frontend]]). The repo root keeps only
what is shared: `Taskfile.yml`, `compose.yml`, `.github/` (CI and Dependabot), `.claude/`,
`documentation/` and the top-level docs.

The one rule to remember: **Python commands run with `backend/` as the working directory**.
`alembic.ini` (`prepend_sys_path = .`), the template path `resources/rajtlista.docx`, pytest's
rootdir (`from app import app`), `--cov=lineup` and the default SQLite file `./lineup.db` are all
relative to the current directory. The `task` commands set `dir: backend` for you, so run them
from anywhere; if you call `uv`, `pytest` or `alembic` by hand, `cd backend` first. Paths
elsewhere on this page (e.g. `tests/`, `Dockerfile`, `pyproject.toml`) are relative to `backend/`.

## Dev workflow (`Taskfile.yml`)

| Task | Purpose |
|---|---|
| `task install` | `uv sync` — install dependencies |
| `task doctor` | check the required tools and their minimum versions (`scripts/doctor.sh`); the first step of [[Setup]] |
| `task test` | pytest with coverage (must pass at 100%; e2e tests excluded) |
| `task test-e2e` | build image, start container, run real-conversion fidelity tests, tear down |
| `task lint` / `task format` | `ruff check` / `ruff format` |
| `task serve` | local uvicorn dev server, loads `backend/.env` (no PDF support — no LibreOffice locally; DB tables auto-created on startup for SQLite via `AUTO_CREATE_SCHEMA=1`) |
| `task db:status` / `task db:postgres` / `task db:sqlite` | show / switch which database `backend/.env` selects (Supabase pooler vs. local SQLite) |
| `task run` | run `main.py`, the CLI demo that writes one hard-coded lineup to `resources/modified_rajtlista.docx` |
| `task build` / `task rebuild` | build container image (`lineup`) / force fresh build with `--no-cache` |
| `task up` / `task down` | start/stop the container |
| `task migrate` / `task migrate-new -- -m "..."` / `task migrate-down` | Alembic upgrade / autogenerate / rollback one step |
| `task migrate-check` | Apply all migrations to a throwaway SQLite file, then `alembic check` (fails on model/migration drift). CI runs it |
| `task migrate:supabase` | Apply migrations to Supabase using `MIGRATE_DATABASE_URL` from `backend/.env.migrate` (owner credentials, kept out of `.env`) |
| `task db:create-app-role` | Give the `lineup_app` role a generated password (asks for a typed `yes` first, since a re-run rotates it) and point `backend/.env`'s pooler URL at it (password never printed) |
| `task docs:references` / `task docs:check` | regenerate / verify the dependency block in `documentation/References.md` (`scripts/docs_references.py`) |

## Configuration (environment variables)

All runtime configuration is via environment variables, documented in `backend/.env.example` (copy it
to the git-ignored `backend/.env`). With no `backend/.env` the app runs entirely on local SQLite with no
external services.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lineup.db` | Which database to use — SQLite locally, Supabase Postgres via a `postgresql+asyncpg://` URL. See [[Current State: Backend]] for the exact URLs |
| `AUTO_CREATE_SCHEMA` | unset | Opt-in (`1`/`true`/`yes`): create the tables from the ORM models on startup. Only honoured for SQLite, never for Postgres (Alembic owns that schema). `task serve` and the default Compose setup set it |
| `ENV` | unset | `production` = fail closed at startup and no API docs. Set it for any real Postgres (dev or prod). It makes startup fail closed (needs a `postgresql+asyncpg` `DATABASE_URL` with `ssl=require`/`verify-full` and `SUPABASE_URL`) and turns the API docs off |
| `CORS_ORIGINS` | unset | Comma-separated browser origins allowed to call the API. Unset = no CORS headers; `*` is refused at startup |
| `APP_BASE_URL` | `http://localhost:5173` | The web app's origin; team invite links are `<APP_BASE_URL>/join/<code>`. Set in `fly.toml` to the Pages URL |
| `DOCS_ENABLED` | `true` | Serve `/docs`, `/redoc`, `/openapi.json`; always off when `ENV=production` |
| `MAX_BODY_BYTES` | `262144` | Request body cap in bytes; bigger bodies get `413` |
| `RATE_LIMIT_GENERATE_PER_USER` / `RATE_LIMIT_GENERATE_PER_IP` | `10` / `30` | Document generations per minute per signed-in user / per client IP (`429` + `Retry-After`). In-memory, per process |
| `CLIENT_IP_HEADER` | unset | Header with the real client IP for the per-IP limit (Fly.io: `Fly-Client-IP`); set it only when the proxy overwrites it. Unset = TCP peer address |
| `SUPABASE_URL` | unset | Supabase project URL; the API derives the token issuer and JWKS address from it. Unset = protected routes answer `503` (see [[Auth Setup]]) |
| `PDF_MAX_CONCURRENT` | `2` | Max parallel LibreOffice conversions; extra requests wait 10 s, then get `503` + `Retry-After` |
| `SENTRY_DSN` | unset | Enables Sentry error monitoring (see below) |

`task up` (Docker Compose, through `env_file: backend/.env` in the root `compose.yml`) passes these into the container;
`task serve` sources it too. `task migrate` / `task migrate-new` do not (they target SQLite
unless `DATABASE_URL` is passed for one run). `task db:postgres` / `task db:sqlite` /
`task db:status` switch and report which database `backend/.env` selects. Never commit `backend/.env` — it is
git-ignored.

## Containerization

- `backend/Dockerfile` is a two-stage build. Both stages start from `python:3.14-slim`, **pinned by
  digest** so a rebuild can't silently change the base (the Dependabot docker ecosystem opens the
  bump PRs). The *builder* stage installs the Python dependencies with the pinned `uv` image
  (`uv sync --frozen --no-dev`, bytecode-compiled). The *runtime* stage adds LibreOffice and the fonts
  and copies the finished virtualenv in, so `uv` isn't in the image that runs. It also removes `pip`:
  the venv is already built, and pip's vendored copies of urllib3, certifi, msgpack and setuptools were
  the source of the image's Trivy alerts. The image is on 3.14, not 3.15, because lxml, pydantic-core
  and four other locked packages have no 3.15 wheels yet (a 3.15 build would need a compiler toolchain).
- **Least privilege**: the container runs as the unprivileged `app` user (uid 10001) that owns `/app`
  (the default SQLite file is created there), and Compose drops all Linux capabilities and sets
  `no-new-privileges`. LibreOffice needs none of them. Check with `docker run --rm lineup id -u`
  (anything but `0`).
- **tini** is PID 1. LibreOffice leaves `soffice.bin` child processes behind, and PID 1 is responsible
  for reaping orphans; without an init process they pile up as zombies. tini also forwards signals, so
  `docker stop` returns immediately instead of waiting out the 10 s kill timeout.
- **Healthcheck**: the image polls `GET /health` (liveness only: a database outage must not make an
  orchestrator restart a healthy API). curl isn't installed, so it uses the Python interpreter.
  `docker compose up --wait` (used by `task test-e2e`) blocks until it reports healthy.
- **Smaller image**: `libreoffice-writer-nogui` instead of the full `libreoffice` metapackage drops the
  GUI toolkits and the other office apps; the e2e fidelity tests still pass. The image went from about
  1.16 GB to 870 MB.
- **Font fidelity**: the template is authored in Calibri/Calibri Light (proprietary).
  `--no-install-recommends` is kept, so the metric-compatible substitutes are installed
  explicitly: `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea`
  (Cambria), `fonts-liberation2` (Arial/Times/Courier).
  `backend/docker/fontconfig/99-calibri-carlito.conf` forces Calibri → Carlito and `fc-cache -f`
  refreshes the cache — without this, LibreOffice substitutes a differently-sized font and
  the tab-stop/table layout drifts in the PDF.
- The Docker build context is `backend/` (`docker build -t lineup backend`), so nothing at the
  repo root (`.github/`, `.claude/`, `documentation/`, `frontend/`, Compose/Taskfile) can ever
  reach the image. `backend/.dockerignore` matters for **security**, not just size: the
  Dockerfile does `COPY . .`, so anything not excluded ends up in an image layer. It excludes
  `.env`/`.env.*` (the Supabase credentials in `backend/.env` sit *inside* the context) and
  `*.db` (local SQLite data), plus tests, `*.md`, caches and `.git`. Check it whenever a new
  secret or local-state file appears in `backend/`. The image ships without tests, which is why the
  e2e suite runs from the host against the running container rather than inside the image.
- The container starts `uvicorn` straight from the virtualenv's `bin` directory (which is on `PATH`):
  the dependencies were installed at build time, so nothing is resolved or synced at start. It runs with
  `--no-access-log`, because invite codes are URL path segments and uvicorn's access log would print
  them (with the client IP) into the platform logs.
- `compose.yml` (repo root) uses `image: lineup` (not `build:`), so `task build`/`task rebuild` is
  always required before `task up`. It takes its settings from `env_file: backend/.env`
  (`required: false`, Compose >= 2.24) — Compose's own `.env` lookup only checks next to
  `compose.yml`, so it would no longer see `backend/.env` — and the container falls back to its
  SQLite default when the file is absent. That default is `sqlite+aiosqlite:////data/lineup.db`
  (set as `ENV DATABASE_URL` in the Dockerfile; `env_file` and Fly's secret override it), and
  `/data` is the named volume `lineup-data`, so the data survives `task down`, `task rebuild`
  and a reboot. The port is published on `127.0.0.1` only (the API must not be reachable from the
  LAN) and the service has `restart: unless-stopped`; the image's own `HEALTHCHECK` on `/health` is
  inherited. Full reset: `task down` → `docker compose down -v` (deletes the volume and with it the
  local data) → `docker rmi lineup` → `docker image prune` → `task rebuild` → `task up`.
- Containers can be monitored with `lazydocker`.
- PDF conversion **only works inside the container** — it's why the API must be run via
  `task build` + `task up`, not `task serve`.
- **Hosting (dev):** `backend/fly.toml` describes the Fly.io app `lineup-dev-lb`: the same image,
  region `ams` (EU, next to the Supabase project in `eu-west-1`), scale to zero, 1 GB of memory
  for LibreOffice and a `GET /health` check. It holds no secrets: `DATABASE_URL`, `SUPABASE_URL`
  and `CORS_ORIGINS` are set with `fly secrets set`. A test (`tests/test_fly_config.py`) fails on
  a non-EU region or a secret-looking key. The one-off setup is in [[Fly Setup]]. A push to
  `develop` that changes `backend/` deploys automatically (`.github/workflows/deploy-dev.yml`, #8):
  Alembic `upgrade head`, `flyctl deploy --ha=false`, then a retrying `/health?db=1` check, then a
  second job that runs the live smoke test (`scripts/smoke_live.py`, #190) against the dev database
  as `lineup_app`. It needs the `FLY_API_TOKEN`, `MIGRATE_DATABASE_URL` and `SMOKE_DATABASE_URL`
  Actions secrets (see *Continuous deployment* in [[Fly Setup]]) and is guarded by
  `tests/test_deploy_workflow.py`.
- **Hosting (dev frontend):** Cloudflare Pages serves `frontend/` (build `pnpm build`, output
  `dist`, production branch `develop`) and builds a static preview per PR. Only public `VITE_*`
  values are set there; the baseline security headers live in `frontend/public/_headers`. Its
  origin goes into the Fly `CORS_ORIGINS` secret and the Supabase redirect list. The one-off setup
  is in [[Pages Setup]].

## Testing

- `pyproject.toml` enforces `fail_under = 100` coverage.
- Every module has a corresponding `tests/test_<module>.py`.
- Any code calling LibreOffice must mock `PdfConverter.convert` — it isn't available
  locally. `test_api.py` has an `autouse` fixture that patches it for all PDF-triggering
  endpoint tests.
- `tests/test_pdf_conversion_e2e.py` is the one exception: it drives the **real** conversion
  against the running container, marked `e2e` and excluded from `task test`
  (`addopts = "-m 'not e2e'"`) so it never affects coverage. Run via `task test-e2e`. It
  talks to the API over HTTP (stdlib `urllib`) and validates layout with `pdfplumber`
  (single page, expected text, word widths/positions vs. `expected-rajtlista.pdf`) — it does
  **not** pixel-diff, since the reference uses real Calibri and the container uses
  metric-compatible Carlito.
- DB tests use the `async_client` fixture (`tests/conftest.py`) — a fresh in-memory SQLite
  DB per test, with `get_session` and `get_current_user_id` dependency-overridden (the
  `current_user` fixture holds the signed-in user's id; assign a new one mid-test to act as a
  second user, see `tests/test_tenant_isolation.py`). The real token check is tested in
  `tests/test_auth_dependencies.py` with throw-away generated keys and no network. CI never
  talks to a real Postgres: the Postgres-specific engine branches are tested by constructing
  (lazy, never-connecting) engines, and tests ignore any local `backend/.env`.
- Team-membership scoping is tested both through the API with two users
  (`tests/test_tenant_isolation.py`, which also proves teammates share a roster) and directly against the
  `db_session` fixture in the repository tests. Most API tests need a team first: `tests/helpers.py`
  has `ensure_team()` / `create_player()`.

### The coverage/greenlet gotcha

`[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet", "thread"]`.
SQLAlchemy's async ORM bridges sync calls onto greenlets (`greenlet_spawn`); without this
setting, `coverage.py` silently drops line hits for code *after* a greenlet-based await
resumes (e.g. the line right after `await session.commit()`), even though it genuinely ran.
This looked like a real ~90%-coverage shortfall across every DB-touching module until it was
traced to this missing config — worth remembering if coverage ever looks impossibly low
again on async DB code.

## Continuous Integration

Four GitHub Actions workflows (`.github/workflows/`):

- **`ci.yml`** — runs on every PR (and push) against `develop` or `main`: `task lint` (`ruff check .`,
  including flake8-bandit's `S` security rules), `ruff format --check .`, `task test` (100%
  coverage), then `task test-e2e` (builds the image, runs a container, verifies real PDF
  conversion fidelity), then scans the built image for vulnerabilities with Trivy. The
  `arduino/setup-task` steps pass `repo-token: ${{ secrets.GITHUB_TOKEN }}` so the action's
  GitHub API lookups are authenticated; without it, shared runners occasionally hit the
  unauthenticated rate limit and the job fails before any of our code runs. The input really is
  `repo-token`: an unknown input such as `github-token` is ignored with only an
  "Unexpected input(s)" warning, which is how an earlier version of this fix silently did nothing.
- **`docs-check.yml`** — on every PR (also when labels change, which is why it is not part of
  `ci.yml`: re-running the e2e job for a label would be wasteful): runs
  `scripts/check_docs_touched.sh`, which fails when the diff touches code or config paths
  (`backend/lineup/`, `backend/alembic/`, `backend/app.py`, `pyproject.toml`, `Dockerfile`,
  `.env.example`, `compose.yml`, `Taskfile.yml`, `scripts/`, workflows, `frontend/src/`)
  but none of `README.md`, `CLAUDE.md`, `.claude/rules/`, `.claude/context/` or `documentation/`. The escape hatch for changes that
  genuinely need no documentation is the `no-docs` label together with a
  `No doc impact: <reason>` line in the PR description. Dependabot PRs are skipped. The job
  is read-only (`contents: read`) and passes labels through `env:` rather than interpolating
  them into the script. **Why a check at all:** docs drifted whenever updating them depended
  on someone remembering; a failing check makes "did you update the docs?" part of review.
- **`wiki-sync.yml`** — on push to `develop` touching `documentation/**`: mirrors this folder
  into the GitHub wiki (with an explicit filename-rename map, since wiki filenames preserve
  colons but `documentation/`'s filenames don't, for filesystem portability). The map is
  explicit, so a page missing from it would silently never be published: the workflow now
  fails when a `documentation/*.md` file is not in the map, and `tests/test_docs_tooling.py`
  checks the same thing on every PR.
- **`release.yml`** — by hand (#17): checks that `backend/pyproject.toml` and `frontend/package.json` carry the same
  untagged `MAJOR.MINOR.PATCH` version, then creates the `vX.Y.Z` tag and a GitHub Release (pre-release below 1.0)
  with generated notes and the Alembic migrations added since the last tag. It needs only `contents: write`, no
  secrets, and runs from `develop` or `main`. The bump itself is `task release:bump` in a normal PR.
- **`keepalive.yml`** — on Mondays and Thursdays (and by hand): runs `SELECT 1` through the Supabase
  transaction pooler with the `KEEPALIVE_DATABASE_URL` Actions secret (a plain `postgresql://…?sslmode=require`
  URL, not the app's asyncpg one, which `psql` rejects), so the free-tier dev project never
  reaches its inactivity pause (a paused project also takes Supabase Auth down). Twice a week means one
  failed run is not enough to let it pause; GitHub emails the person who last changed the `cron:` line
  when a run fails. It uses no third-party actions (`psql` ships with the runner). GitHub disables scheduled
  workflows after 60 days without repo activity, and a disabled workflow doesn't fail, so after a long break
  check the Actions tab and re-enable it.

`ci.yml` has five jobs. **Frontend** installs the frontend with a frozen pnpm lockfile and runs ESLint and
Prettier, the type check, the Vitest suite with a coverage report (it fails below 100 %, set in `frontend/vite.config.ts`) and the production build, then `task fe:api:check`, which
regenerates the API client from the backend's OpenAPI spec (`scripts/dump_openapi.py`, no server)
and fails if the committed `frontend/src/api/` differs; a report-only `pnpm audit --prod` closes it.
It deliberately has no path filter, so it reports on every PR, which is what lets it be a required check
on `develop` and `main`. **Lint & test** runs ruff, the tests at 100% coverage, the References check and
`task migrate-check` (migrations applied to SQLite, then `alembic check`). **Migrations (Postgres)** starts
a throwaway Postgres 17 service container, migrates it from scratch and asserts what SQLite cannot: RLS
on every table, the event trigger, the `lineup_app` grants, no access for `anon`/`authenticated`
(`tests/test_postgres_migrations.py`), then `alembic check` with type comparison and a
`downgrade base` / `upgrade head` round trip. **E2E** builds the image and runs the real-conversion tests. **Frontend browser tests** (report only, `continue-on-error`, so it never blocks a PR until it has proven stable) installs Chromium and runs `task fe:e2e`: Playwright against the production build at a phone and a desktop size with the network mocked, uploading the traces of a failed run for 7 days.

`ci.yml`'s `Lint & test` job also runs `task docs:check`, which fails when the generated block of
`documentation/References.md` no longer matches `backend/pyproject.toml`, the `Dockerfile` or the
workflows. The block lists package *names* only (no versions), so Dependabot version bumps don't
turn it red; only adding or removing a dependency does, and `task docs:references` fixes it.

### Security & observability tooling

- **Dependency updates**: `.github/dependabot.yml` opens weekly PRs against the `uv`
  ecosystem (`directory: /backend`, i.e. `backend/pyproject.toml`/`backend/uv.lock`), the `docker` ecosystem (`backend/Dockerfile`: the
  digest-pinned base image and the `uv` image) the `npm` ecosystem (`directory: /frontend`, i.e. `frontend/package.json`/`frontend/pnpm-lock.yaml`, minor and patch updates grouped into one PR) and the `github-actions` ecosystem (the workflow
  files). Every ecosystem groups its minor and patch updates into one PR; majors stay separate. Security-alert PRs are governed separately by the repo's "Dependabot security
  updates" setting (a GitHub repo setting, not a file in this repo).
- **Secret scanning**: GitHub secret scanning + push protection are already enabled at the
  repo level — no code/config here, just a setting.
- **Static analysis (SAST)**: `ruff`'s `S` rule category (flake8-bandit) is enabled via
  `[tool.ruff.lint] extend-select = ["S", "D1"]` in `pyproject.toml` (`D1` is pydocstyle's "missing docstring" family only, so `task lint` fails when a public module, class, function or method has no docstring; `tests/**` and `alembic/versions/*.py` are exempt. The *content* of a docstring is checked in review and by the `update-documentation` skill). `tests/**` gets `S101`
  (`assert`) and `S310` (`urlopen` scheme check against a fixed local constant in the e2e
  test) ignored via `per-file-ignores`, since both are expected patterns in test code, not
  risks. `lineup/document/pdf_converter.py` gets `S603`/`S607` (subprocess call / partial
  executable path) ignored the same way — its `subprocess.run([...])` call uses a literal
  executable name and an argv list with no `shell=True` and no user-controlled input, so
  neither warning reflects a real risk there.
- **Container image scanning**: `aquasecurity/trivy-action` scans the built `lineup:latest`
  image in the `e2e` CI job (severity `CRITICAL,HIGH`, `ignore-unfixed: true`). Both the
  table-format and SARIF-format runs are pinned to `exit-code: "0"` — this is deliberately
  **report-only**, never failing the build, because the LibreOffice + apt package surface has
  more CVEs than a plain slim-Python image can realistically stay ahead of. SARIF results are
  uploaded to the repo's Security → Code scanning tab via `github/codeql-action/upload-sarif`
  for persistent, filterable tracking.
- **Error monitoring**: `sentry-sdk[fastapi]` is initialized in `app.py` at import time,
  gated on the `SENTRY_DSN` environment variable (`os.getenv`, no default — unset means
  disabled). `traces_sample_rate=0.0` — errors only, no performance tracing, matching the
  Sentry free "Developer" tier. Unset in local dev, CI, and tests, so no network call is ever
  attempted by default; see `tests/test_app.py` for the (mocked) coverage of both branches.
- **Logging**: no dedicated logging tooling yet — see [[Roadmap: Everything Else]] for the
  deferred plan (this project has no live deployment to point a log viewer at today).

## Claude Code tooling

**Project context is split by area so a session loads only what it needs.** `CLAUDE.md` is a router (summary, always-on
rules, a "working on X → read Y" table, capped at 100 lines by a test). The detail lives in
`.claude/rules/*.md`, each with a `paths:` list in its frontmatter: Claude Code loads a rule only when it reads or edits a
matching file (for example `backend-db.md` for `backend/lineup/db/**`). `.claude/context/*.md` (workflow, the pre-PR
Dependabot checklist, the skills description) is read on demand by the router and the skills. A rule without `paths:` would
load every session, so a test requires every rule to be path-scoped and every glob to match a file. The built-in Explore
and Plan subagents load neither `CLAUDE.md` nor the rules, so a prompt to them names the rule file to read. Editing any of
these files counts as a docs change for CI's docs gate. Two working agreements live in `.claude/context/workflow.md` ("Who may commit, push, open and merge"): work based on
a pre-agreed issue may be committed, pushed, PR'd and merged (green checks, merge commit) without asking each time,
because the agreed ticket is the approval, while anything without one still needs confirmation; and subagents are
used for a task where that is possible and reasonable. The file tree lives only in `README.md`.

The repo ships skills in `.claude/skills/` for the workflows that repeat. Each one is a
Markdown playbook Claude follows when a request matches its description. They exist so these
procedures run the same way every time instead of being reconstructed from memory.

**Where they come from.** `compliance-audit` and `supabase-smoke` are lineup-only. The other six
skills and the read-only `convention-reviewer` agent (`.claude/agents/`) are generic: they live in
the owner's private `ai-common` repo and are installed with [APM](https://github.com/microsoft/apm)
(Agent Package Manager). `apm.yml` pins the `ai-common` tag and `apm.lock.yaml` records the
commit and a hash of every installed file. A generic skill holds only the procedure; it reads
lineup's values from `.claude/context/` (`issues.md`, `pr-checklist.md`, `docs.md`, `audit.md`),
so the same skill can serve other projects. The installed copies are committed, which keeps the
public repo usable without access to `ai-common`. Changing one means changing it in `ai-common`,
tagging a release and re-running `apm install` here (`.claude/context/claude-code.md`):

| Skill | Source |
|---|---|
| `compliance-audit`, `supabase-smoke` | lineup |
| `new-issue`, `create-pr`, `triage-dependabot`, `update-documentation`, `repo-audit`, `setup-project`; agent `convention-reviewer` | `ai-common` (APM) |

What each one does:

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

`model:` in a skill's frontmatter pins the model only while that skill runs: opus for the
cross-cutting analysis, sonnet for the multi-step git/docs work, haiku for templated steps.
The value is always an alias (`opus`, `sonnet`, `haiku`): Claude Code resolves it to the newest
model of that tier, so the skills follow new releases by themselves, and a test rejects a
full model ID. If a skill seems to run an older model, check the
`ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` environment variables on your machine: they
override what the aliases resolve to. Every skill that writes to GitHub, git or
Supabase asks before each state-changing command. The shared `.claude/settings.json` lets
`task lint`/`task test` run without prompting and denies reading `.env*` (at the root and in `backend/`), so credentials
never enter the conversation.

**Issue conventions** (the values `new-issue` reads from `.claude/context/issues.md`):
- Bodies follow Problem / Evidence / Proposal / Acceptance.
- Issues opened on GitHub itself use the forms in `.github/ISSUE_TEMPLATE/` (bug, feature, chore; blank issues are off). A form can only set the `type:*` label, so a maintainer adds `area:*`, `priority:*`, `plan:*` and the milestone.
- Labels: one `type:*`, one or more `area:*`, one `priority:*`, and one `plan:*` (keep, keep-cheap, defer, drop).
- Milestones: M1 Hardening, M3 Dev preview, Mx Parked (deliberately not now; M2 Prod is closed).
- Work is grouped under epics (#41–#46, the frontend epic #20, the compliance epic #92) as GitHub sub-issues, with
  blocked-by links for ordering.
- The single "Lineup" project board carries Status/Area/Priority/Size, and its Auto-add
  workflow puts new issues on it.

## Conventions (OpenAPI / FastAPI)

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's
  query parameter introspection.
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to
  appear in the docs.
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI
  renders enums from `$ref` correctly.
- A `-> Response` return annotation for raw binary output does **not** suppress
  query-parameter display in the OpenAPI spec — FastAPI derives query params from the
  function signature, not the return annotation.
