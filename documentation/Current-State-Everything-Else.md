# Current State: Everything Else

Cross-cutting concerns: dev workflow, containerization, testing, and conventions that apply
across the backend regardless of which module you're touching.

## Repository layout

The repo is split so each side can be built, tested and deployed on its own: **`backend/`**
holds all the Python (API, Alembic migrations, tests, `Dockerfile`, `pyproject.toml`, the
`.docx` template), and **`frontend/`** will hold the web app. The repo root keeps only
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
| `task test` | pytest with coverage (must pass at 100%; e2e tests excluded) |
| `task test-e2e` | build image, start container, run real-conversion fidelity tests, tear down |
| `task lint` / `task format` | `ruff check` / `ruff format` |
| `task serve` | local uvicorn dev server, loads `backend/.env` (no PDF support — no LibreOffice locally; DB tables auto-created on startup unless `ENV=production`) |
| `task db:status` / `task db:postgres` / `task db:sqlite` | show / switch which database `backend/.env` selects (Supabase pooler vs. local SQLite) |
| `task run` | run `main.py`, the CLI demo that writes one hard-coded lineup to `resources/modified_rajtlista.docx` |
| `task build` / `task rebuild` | build container image (`lineup`) / force fresh build with `--no-cache` |
| `task up` / `task down` | start/stop the container |
| `task migrate` / `task migrate-new -- -m "..."` / `task migrate-down` | Alembic upgrade / autogenerate / rollback one step |
| `task migrate-check` | Apply all migrations to a throwaway SQLite file, then `alembic check` (fails on model/migration drift). CI runs it |
| `task migrate:supabase` | Apply migrations to Supabase using `MIGRATE_DATABASE_URL` from `backend/.env.migrate` (owner credentials, kept out of `.env`) |
| `task db:create-app-role` | Give the `lineup_app` role a generated password and point `backend/.env`'s pooler URL at it (password never printed) |
| `task docs:references` / `task docs:check` | regenerate / verify the dependency block in `documentation/References.md` (`scripts/docs_references.py`) |

## Configuration (environment variables)

All runtime configuration is via environment variables, documented in `backend/.env.example` (copy it
to the git-ignored `backend/.env`). With no `backend/.env` the app runs entirely on local SQLite with no
external services.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lineup.db` | Which database to use — SQLite locally, Supabase Postgres via a `postgresql+asyncpg://` URL. See [[Current State: Backend]] for the exact URLs |
| `ENV` | unset | `production` = "schema is Alembic-managed, skip `create_all` on startup". Set it for any real Postgres (dev or prod) |
| `CORS_ORIGINS` | unset | Comma-separated browser origins allowed to call the API. Unset = no CORS headers; `*` is refused at startup |
| `PDF_MAX_CONCURRENT` | `2` | Max parallel LibreOffice conversions; extra requests wait 10 s, then get `503` + `Retry-After` |
| `SENTRY_DSN` | unset | Enables Sentry error monitoring (see below) |

`task up` (Docker Compose, through `env_file: backend/.env` in the root `compose.yml`) passes these into the container;
`task serve` sources it too. `task migrate` / `task migrate-new` do not (they target SQLite
unless `DATABASE_URL` is passed for one run). `task db:postgres` / `task db:sqlite` /
`task db:status` switch and report which database `backend/.env` selects. Never commit `backend/.env` — it is
git-ignored.

## Containerization

- `backend/Dockerfile` is a two-stage build. Both stages start from `python:3.13-slim`, **pinned by
  digest** so a rebuild can't silently change the base (the Dependabot docker ecosystem opens the
  bump PRs). The *builder* stage installs the Python dependencies with the pinned `uv` image
  (`uv sync --frozen --no-dev`, bytecode-compiled). The *runtime* stage adds LibreOffice and the fonts
  and copies the finished virtualenv in, so `uv` isn't in the image that runs.
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
  the dependencies were installed at build time, so nothing is resolved or synced at start.
- `compose.yml` (repo root) uses `image: lineup` (not `build:`), so `task build`/`task rebuild` is
  always required before `task up`. It takes its settings from `env_file: backend/.env`
  (`required: false`, Compose >= 2.24) — Compose's own `.env` lookup only checks next to
  `compose.yml`, so it would no longer see `backend/.env` — and the container falls back to its
  SQLite default when the file is absent. Full reset: `task down` → `docker rmi lineup` →
  `docker image prune` → `task rebuild` → `task up`.
- Containers can be monitored with `lazydocker`.
- PDF conversion **only works inside the container** — it's why the API must be run via
  `task build` + `task up`, not `task serve`.

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
  DB per test, with `get_session` and `get_current_user_id` dependency-overridden. CI never
  talks to a real Postgres: the Postgres-specific engine branches are tested by constructing
  (lazy, never-connecting) engines, and tests ignore any local `backend/.env`.
- The `owner_id`/`user_id`-scoped filtering branches can't be reached through the API yet
  (since `get_current_user_id()` always returns `None`) — they're tested directly against
  the `db_session` fixture with real non-`None` IDs instead.

### The coverage/greenlet gotcha

`[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet", "thread"]`.
SQLAlchemy's async ORM bridges sync calls onto greenlets (`greenlet_spawn`); without this
setting, `coverage.py` silently drops line hits for code *after* a greenlet-based await
resumes (e.g. the line right after `await session.commit()`), even though it genuinely ran.
This looked like a real ~90%-coverage shortfall across every DB-touching module until it was
traced to this missing config — worth remembering if coverage ever looks impossibly low
again on async DB code.

## Continuous Integration

Three GitHub Actions workflows (`.github/workflows/`):

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
  `.env.example`, `compose.yml`, `Taskfile.yml`, `scripts/`, workflows, later `frontend/src/`)
  but none of `README.md`, `CLAUDE.md` or `documentation/`. The escape hatch for changes that
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

`ci.yml` has three jobs. **Lint & test** runs ruff, the tests at 100% coverage, the References check and
`task migrate-check` (migrations applied to SQLite, then `alembic check`). **Migrations (Postgres)** starts
a throwaway Postgres 17 service container, migrates it from scratch and asserts what SQLite cannot: RLS
on every table, the event trigger, the `lineup_app` grants, no access for `anon`/`authenticated`
(`tests/test_postgres_migrations.py`), then `alembic check` with type comparison and a
`downgrade base` / `upgrade head` round trip. **E2E** builds the image and runs the real-conversion tests.

`ci.yml`'s `Lint & test` job also runs `task docs:check`, which fails when the generated block of
`documentation/References.md` no longer matches `backend/pyproject.toml`, the `Dockerfile` or the
workflows. The block lists package *names* only (no versions), so Dependabot version bumps don't
turn it red; only adding or removing a dependency does, and `task docs:references` fixes it.

### Security & observability tooling

- **Dependency updates**: `.github/dependabot.yml` opens weekly PRs against the `uv`
  ecosystem (`directory: /backend`, i.e. `backend/pyproject.toml`/`backend/uv.lock`), the `docker` ecosystem (`backend/Dockerfile`: the
  digest-pinned base image and the `uv` image) and the `github-actions` ecosystem (the workflow
  files). Security-alert PRs are governed separately by the repo's "Dependabot security
  updates" setting (a GitHub repo setting, not a file in this repo).
- **Secret scanning**: GitHub secret scanning + push protection are already enabled at the
  repo level — no code/config here, just a setting.
- **Static analysis (SAST)**: `ruff`'s `S` rule category (flake8-bandit) is enabled via
  `[tool.ruff.lint] extend-select = ["S"]` in `pyproject.toml`. `tests/**` gets `S101`
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

The repo ships project skills in `.claude/skills/` for the workflows that repeat. Each one is a
Markdown playbook Claude follows when a request matches its description. They exist so these
procedures run the same way every time instead of being reconstructed from memory:

| Skill | Model | Use it to |
|---|---|---|
| `repo-audit` | opus | audit the whole repo (code, docs/infra/CI, GitHub state) with three parallel explorers, verify the serious findings, then reconcile them with issues and the board — the process behind epics #40–#46 |
| `compliance-audit` | opus | check the repo against GDPR, the Hungarian rules and the OWASP baseline (`requirements.md` next to the skill: what is required, why, where to look), then turn the gaps into issues under epic #92. `quick <issue#\|branch>` is a few-minute check of a single feature, run when its implementation starts and as a `create-pr` gate, so privacy work is planned up front rather than found later |
| `new-issue` | haiku | file or restructure an issue the project's way: Problem/Evidence/Proposal/Acceptance body, `type:`/`area:`/`priority:` labels, milestone, board fields, parent epic, blocked-by links |
| `triage-dependabot` | sonnet | check Dependabot alerts and PRs and classify each PR as blocking/non-blocking (the pre-PR rule in `CLAUDE.md`) |
| `create-pr` | sonnet | get a branch PR-ready (Dependabot triage, lint/test/e2e, docs sync) and open the PR with `Closes`/`Refs` links |
| `supabase-smoke` | haiku | run the live create/generate/delete smoke test against the dev Supabase project after model or engine changes |
| `update-documentation` | — | sync `README.md`, `CLAUDE.md` and `documentation/` after a change |
| `setup-project` | — | set up a fresh clone |

`model:` in a skill's frontmatter pins the model only while that skill runs: opus for the
cross-cutting analysis, haiku for templated steps. Every skill that writes to GitHub, git or
Supabase asks before each state-changing command. The shared `.claude/settings.json` lets
`task lint`/`task test` run without prompting and denies reading `.env*` (at the root and in `backend/`), so credentials
never enter the conversation.

**Issue conventions** (encoded in `new-issue`):
- Bodies follow Problem / Evidence / Proposal / Acceptance.
- Labels: one `type:*`, one or more `area:*`, one `priority:*`.
- Milestones: M1 Hardening, M2 Prod, M3 Dev preview.
- Work is grouped under epics #40–#46 (and the frontend epic #20) as GitHub sub-issues, with blocked-by links for
  ordering.
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
