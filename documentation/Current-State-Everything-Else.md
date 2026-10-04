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

## Configuration (environment variables)

All runtime configuration is via environment variables, documented in `backend/.env.example` (copy it
to the git-ignored `backend/.env`). With no `backend/.env` the app runs entirely on local SQLite with no
external services.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lineup.db` | Which database to use — SQLite locally, Supabase Postgres via a `postgresql+asyncpg://` URL. See [[Current State: Backend]] for the exact URLs |
| `ENV` | unset | `production` = "schema is Alembic-managed, skip `create_all` on startup". Set it for any real Postgres (dev or prod) |
| `SENTRY_DSN` | unset | Enables Sentry error monitoring (see below) |

`task up` (Docker Compose, through `env_file: backend/.env` in the root `compose.yml`) passes these into the container;
`task serve` sources it too. `task migrate` / `task migrate-new` do not (they target SQLite
unless `DATABASE_URL` is passed for one run). `task db:postgres` / `task db:sqlite` /
`task db:status` switch and report which database `backend/.env` selects. Never commit `backend/.env` — it is
git-ignored.

## Containerization

- `backend/Dockerfile`: `python:3.13-slim` + LibreOffice via `apt` + `uv` for deps.
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
- The container starts with `uv run --no-sync uvicorn ...`: dependencies were installed at
  build time with `uv sync --frozen --no-dev`, and `--no-sync` stops `uv run` from re-syncing
  (and pulling the dev group) at every start.
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

Two GitHub Actions workflows (`.github/workflows/`):

- **`ci.yml`** — runs on every PR (and push) against `develop` or `main`: `task lint` (`ruff check .`,
  including flake8-bandit's `S` security rules), `ruff format --check .`, `task test` (100%
  coverage), then `task test-e2e` (builds the image, runs a container, verifies real PDF
  conversion fidelity), then scans the built image for vulnerabilities with Trivy. The
  `arduino/setup-task` steps pass `repo-token: ${{ secrets.GITHUB_TOKEN }}` so the action's
  GitHub API lookups are authenticated; without it, shared runners occasionally hit the
  unauthenticated rate limit and the job fails before any of our code runs. The input really is
  `repo-token`: an unknown input such as `github-token` is ignored with only an
  "Unexpected input(s)" warning, which is how an earlier version of this fix silently did nothing.
- **`wiki-sync.yml`** — on push to `develop` touching `documentation/**`: mirrors this folder
  into the GitHub wiki (with an explicit filename-rename map, since wiki filenames preserve
  colons but `documentation/`'s filenames don't, for filesystem portability).

### Security & observability tooling

- **Dependency updates**: `.github/dependabot.yml` opens weekly PRs against the `uv`
  ecosystem (`directory: /backend`, i.e. `backend/pyproject.toml`/`backend/uv.lock`) and the `github-actions` ecosystem (the two workflow
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
- Milestones: M1 Hardening, M2 Auth & Prod, M3 Frontend MVP.
- Work is grouped under epics #40–#46 as GitHub sub-issues, with blocked-by links for
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
