# lineup

A tool for generating water polo lineup documents. It takes match details and player information, then fills in a `.docx` template (`backend/resources/rajtlista.docx`) and converts the result to a PDF.

The document can be generated via a REST API, which returns the populated file as a PDF. The API also provides CRUD endpoints for managing teams, players, and saved lineups (persisted in SQLite locally, swappable to Supabase Postgres — currently a dev project; no production deployment exists yet), so a lineup can be built from a saved roster instead of a one-off request payload.

## How it works (start here)

Water polo match officials need a filled-in lineup sheet ("rajtlista") before every game. This project automates that: you give it the match details and the players, it fills a Word template, and hands back a print-ready PDF.

**Document generation** (`POST /lineups`): the request is validated (Pydantic models in `backend/lineup/api/models.py`) and turned into a `WaterPoloLineupDTO`. `WaterPoloLineupCreator` passes it to `DocumentManager`, which fills `backend/resources/rajtlista.docx` using python-docx. For `format=docx` the filled file is returned as is; for `format=pdf` (the default) `PdfConverter` runs LibreOffice in headless mode on it and returns the PDF. LibreOffice only exists inside the container image, which is why the API is run with `task build` + `task up`.

**Persistence layer** (`/teams`, `/players`, `/lineups/saved`): so a lineup can be built from a saved roster instead of retyping everything. Each module (`backend/lineup/teams/`, `backend/lineup/players/`, `backend/lineup/saved_lineups/`) has the same four files: `router.py` (HTTP), `schemas.py` (validation), `service.py` (business rules) and `repository.py` (SQL). Data is stored with SQLAlchemy (async) in a database chosen by the `DATABASE_URL` environment variable: local SQLite by default, Supabase Postgres when configured. Schema changes are managed by Alembic migrations. A saved lineup is a *frozen snapshot* (names copied as text), so deleting a team or player later never alters history.

**Not yet implemented:** real authentication. Every row has an owner column, but it is always empty for now (`get_current_user_id()` returns `None`); adding login later means changing that one function. See the [wiki](https://github.com/LasterBergamot/lineup/wiki) (`documentation/`) for diagrams, the data model and the roadmap; `CLAUDE.md` holds the conventions.

**Repo layout:** all the Python lives in `backend/` (a React frontend will get its own `frontend/` directory); the repo root keeps only shared tooling — `Taskfile.yml`, `compose.yml`, `.github/`, `.claude/`, `documentation/`. Python commands must run with `backend/` as the working directory, because Alembic's config, the `resources/` template paths, pytest's rootdir and the default `./lineup.db` are all cwd-relative. The `task` commands handle that for you (they `cd backend`), so you can run them from the repo root.

**A first tour of the code** (paths relative to `backend/`): `app.py` (wires everything together) → `lineup/api/router.py` (the one-off endpoint) → `lineup/water_polo/` (template filling orchestration) → `lineup/document/` (docx + PDF) → `lineup/db/` (engine and models) → `lineup/teams/` as the example of the persistence layering. `tests/` mirrors the modules one-to-one.

## AI Assistant

This project uses [Claude Code](https://claude.ai/code) as an AI coding assistant. The `CLAUDE.md` file at the root contains the project context that Claude Code reads automatically at the start of every session.

Recurring workflows are packaged as project skills in `.claude/skills/`. Claude picks one up when a request matches its description, or you can call it directly as `/<name>`. Several pin a model in their frontmatter (`model:`), so heavy analysis runs on a stronger model and mechanical steps on a cheaper one, whatever the session default is:

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

Skills that touch GitHub, git or the database still ask before every state-changing command. `.claude/settings.json` is the shared project config: it lets `task lint`/`task test` run without a prompt and blocks Claude from reading `.env` files (at the root and in `backend/`). Personal overrides go in the git-ignored `.claude/settings.local.json`.

## Documentation & wiki

The `documentation/` folder is the source of truth for the project's [GitHub wiki](https://github.com/LasterBergamot/lineup/wiki) content (current-state and roadmap pages, backend/frontend/cross-cutting, plus two reader-oriented pages: the **Newcomer Guide**, a junior-developer walkthrough of the tools, the request flow and how to make a first change, and **References**, the official docs for every library, tool, service, spec and regulation we use). It's mirrored 1:1 into the wiki by `.github/workflows/wiki-sync.yml` on every push to `develop` that touches `documentation/**`. Edit the files here, not the wiki UI directly — direct wiki edits get overwritten by the next sync.

**Keeping the docs current is part of every change.** A PR that touches code or config (`backend/lineup/`, `Dockerfile`, `compose.yml`, `Taskfile.yml`, workflows, …) must also update `README.md`, `CLAUDE.md` or a page under `documentation/`, or say `No doc impact: <reason>` and carry the `no-docs` label. The `Docs updated` check fails otherwise (run `scripts/check_docs_touched.sh origin/develop HEAD` to try it locally). The dependency tables in `documentation/References.md` are generated: run `task docs:references` after changing a dependency, `Dockerfile` or workflow (`task docs:check` verifies it, and CI runs it).

## Branches

There are two environments (dev and prod), so there are two long-lived branches. **`develop`** is the default branch: branch off it and open your PR against it (it will deploy to dev once CD exists). **`main`** is production and only changes through a release PR from `develop` (or a hotfix). Both are protected and require green CI. PRs are merged with a merge commit (no squash/rebase), so keep your branch's commits tidy with `git commit --amend` / `--fixup` rather than adding "fix" commits. See [Roadmap: Everything Else](https://github.com/LasterBergamot/lineup/wiki/Roadmap:-Everything-Else) for the full model, and `PLAN.md` for the planned dev-preview work.

## Continuous Integration

Three GitHub Actions workflows run automatically on GitHub — no local setup or invocation needed to benefit from them:

- **`.github/workflows/ci.yml`** — on every PR (and push) against `develop` or `main`: lints (`ruff check`, including flake8-bandit's `S` security rules), checks formatting (`ruff format --check`), runs the test suite with 100% coverage enforcement, then builds the container, runs the real PDF-conversion e2e test, and scans the built image for vulnerabilities with Trivy (report-only — findings are visible in the job log and the repo's Security tab, but never fail the build, since the LibreOffice-based image has a CVE surface that can't be fully remediated).
- **`.github/workflows/docs-check.yml`** — on every PR: fails if the diff touches code or config without touching `README.md`, `CLAUDE.md` or `documentation/` (escape hatch: the `no-docs` label). `ci.yml` additionally runs `task docs:check`, which fails when the generated part of `documentation/References.md` is stale.
- **`.github/workflows/wiki-sync.yml`** — on push to `develop` that touches `documentation/**`: mirrors those files into the GitHub wiki (and fails if a file in `documentation/` is missing from its page map).

If you're editing the workflow YAML files themselves, `yamllint` and `actionlint` (see [Prerequisites](#prerequisites)) let you validate them locally before pushing.

### Security tooling

- **Dependency updates:** GitHub Dependabot (`.github/dependabot.yml`) opens weekly PRs for outdated Python (`uv`) and GitHub Actions dependencies; security-alert PRs are additionally governed by the repo's "Dependabot security updates" setting.
- **Secret scanning:** GitHub secret scanning + push protection are enabled at the repo level (no code/config in this repo).
- **Static analysis:** `ruff`'s `S` rule category (flake8-bandit) runs as part of `task lint`.
- **Container scanning:** Trivy scans the built image in CI (report-only, see above).
- **Error monitoring:** [Sentry](https://sentry.io) (free Developer tier) — set the `SENTRY_DSN` environment variable in the deployment environment to enable it; errors only, no performance tracing. Unset locally, in CI, and in tests, so nothing is ever sent by default.
- **Logging:** deferred until a real deployment target is chosen — see the "Logging (future)" section of the Roadmap: Everything Else wiki page.

## Prerequisites

Required to install and run the project:

- **Operating System:** Any Linux distribution, preferably **Arch Linux**. On Windows, [Try Omarchy for Windows](https://github.com/omacom/try-omarchy-windows) can be used.
- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — dependency manager
- [Task](https://taskfile.dev/installation/) — task runner
- [Docker Engine](https://docs.docker.com/engine/) & [Docker Compose](https://docs.docker.com/compose/) — container engine and compose (required for PDF conversion via LibreOffice)

Optional, quality-of-life tools:

- [lazydocker](https://github.com/jesseduffield/lazydocker) — terminal UI for Docker containers (recommended for container management)
- [GitHub CLI (`gh`)](https://cli.github.com/) — not required for anything in this repo to work (the CI/wiki-sync workflows run entirely on GitHub's servers regardless), but useful for creating PRs and watching Actions runs (`gh pr create`, `gh pr checks`, `gh run watch`) from the terminal instead of the browser
- [`yamllint`](https://yamllint.readthedocs.io/) & [`actionlint`](https://github.com/rhysd/actionlint) — only needed if you're modifying `.github/workflows/*.yml`; validate the YAML and GitHub Actions semantics locally before pushing (config: `.yamllint`)

## Installation

```bash
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

## Environment variables

Configuration is through environment variables, all optional. `backend/.env.example` documents each one; copy it to `backend/.env` (git-ignored, never commit it) and uncomment what you need.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./lineup.db` | Database to use. SQLite locally, or a Supabase Postgres URL (see below) |
| `ENV` | unset | Set to `production` to skip the automatic table creation on startup because Alembic owns the schema. Set it for **any** real Postgres (dev or prod), despite the name |
| `CORS_ORIGINS` | unset | Comma-separated browser origins allowed to call the API (e.g. `http://localhost:5173` for the Vite dev server). Unset = no CORS headers. `*` is refused at startup |
| `SENTRY_DSN` | unset | Enables Sentry error reporting. Leave unset locally, in CI and in tests |

`task up` (Docker Compose, via `env_file: backend/.env` in `compose.yml`) and `task serve` both load `backend/.env` automatically; it lives in `backend/` beside `backend/.env.example` so it is kept out of the image by `backend/.dockerignore`. `task migrate` and `task migrate-new` deliberately do **not**: they target local SQLite unless you pass `DATABASE_URL` for that one run, so a migration never hits Supabase by accident.

**Switching databases:** `task db:postgres` / `task db:sqlite` flip `backend/.env` between the Supabase pooler and local SQLite (it uncomments or comments the pooler `DATABASE_URL` and adds or removes `ENV=production`), and `task db:status` shows which one is active. Restart `task serve` or run `task up` afterwards to apply the change. `db:postgres` needs a filled-in pooler URL (port 6543) already in `backend/.env`; it never invents one.

### Using the Supabase dev database

The dev environment can run against a hosted Postgres on [Supabase](https://supabase.com) (project `lineup-dev`). This only replaces the database; authentication is not wired up yet.

1. Put the **transaction pooler** URL (port 6543, with `?ssl=require`) in `backend/.env` as `DATABASE_URL`, and set `ENV=production`. Exact URL formats are in `backend/.env.example`. `ENV=production` is the right value for the dev database too: it means "Alembic owns the schema", not "this is the prod deployment". The app uses the pooler rather than the direct connection because the direct host is IPv6-only and, with one fresh connection per request, is slower and burns Postgres's limited connection slots; the direct connection is only needed for the one-off migration in step 2. Tip: `chmod 600 backend/.env` keeps other users on your machine from reading it.
2. Create the tables once with Alembic, using the **direct** connection string (port 5432; the pooler can't run migrations, and on IPv4-only networks use the session-mode pooler instead): `DATABASE_URL="<direct URL>" task migrate`.
3. Start the app (`task up` or `task serve`; both read `backend/.env`).

**Switching back to local SQLite:** run `task db:sqlite` and restart (or comment out `DATABASE_URL` and remove `ENV` in `backend/.env` by hand). Nothing else changes; `task db:postgres` switches forward again.

**If the credentials are lost:** the database password can be reset at any time in the Supabase dashboard (Project Settings → Database → *Reset database password*) without losing data; update your `backend/.env`. API keys and the JWT secret are always viewable and rotatable in Project Settings. The only unrecoverable situation is losing access to the Supabase account itself, so keep the account recovery e-mail and 2FA backup codes safe and consider adding a second owner to the organization.

**Changing the schema later:** edit `backend/lineup/db/models.py`, run `task migrate-new -- -m "description"` (against local SQLite), review the generated file in `backend/alembic/versions/`, then `task migrate` (and the same with the direct `DATABASE_URL` to update Supabase). Moving to a different database or cloud provider someday is covered in the wiki's *Current State: Backend* page.

## API

The API runs inside a container so that LibreOffice is available for PDF conversion. The
image also bundles the libre, metric-compatible fonts (Carlito for Calibri, etc.) that the
template relies on, so the generated PDF matches the source `.docx` layout.

```bash
task build
task up
```

Starts the API server at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs`. You can monitor and manage containers using [lazydocker](https://github.com/jesseduffield/lazydocker).

### `GET /health`

Health probe for the container, deploys and uptime checks. `GET /health` answers `200 {"status":"ok"}` without touching the database (liveness). `GET /health?db=1` also runs `SELECT 1` (readiness) and answers `503 {"status":"unavailable"}` when the database can't be reached; the body never contains driver error text.

### `POST /lineups`

Generates a lineup document from the provided data. Every text field has a maximum length (match, name and staff fields 200, team name 120, division 100, date 50, NSSZ number 50 characters); longer values are rejected with `422`.

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
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..pdf"; filename*=UTF-8''rajtlista_SZVTK_2024.%2012.%2021..pdf

# DOCX
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..docx"; filename*=UTF-8''rajtlista_SZVTK_2024.%2012.%2021..docx
```

The header carries the name twice. HTTP headers are latin-1, so a team name with `ő`/`ű` can't go into plain `filename="..."`. The real UTF-8 name goes in `filename*` (RFC 6266), which browsers prefer; `filename` is an accent-stripped ASCII fallback (`Szőreg` → `Szoreg`).

**Errors:** `422` for invalid input, `504` if LibreOffice doesn't finish the PDF conversion within 120 s, `500` for any other rendering failure. The same rendering, headers and errors apply to `POST /lineups/saved/{id}/generate`. Conversion runs in a worker thread, so a slow PDF never blocks the other endpoints.

### Teams, Players & Saved Lineups

Backed by a SQLite database (in-memory for tests, file-backed at `backend/lineup.db` for local dev via `task serve`, swappable to Supabase Postgres via `DATABASE_URL` — see [Environment variables](#environment-variables)). Text input is checked everywhere the same way: values are trimmed, must not be empty or whitespace-only, and must not contain control characters (tabs, newlines, NUL…), all with `422`. Optional fields treat a blank value as "not provided". Lists come back in a stable order (teams by name, players and saved lineups by creation time, with the id as tie-breaker) so pages never repeat or skip rows, and a saved lineup's players are always sorted by cap number. All list endpoints are paginated: `?limit=20&offset=0` (`limit` is 1–200; there is no "return everything" mode, page with `offset`), in the envelope `{ "items": [...], "total": ..., "limit": ..., "offset": ... }`.

| Method | Path | Description |
|--------|------|--------------|
| `GET`/`POST` | `/teams` | List / create teams |
| `GET` | `/teams/pool?search=&limit=` | Search the shared pool of public teams (for opponent selection) — plain list, not paginated. `search` is a literal, case-insensitive substring (`%` and `_` are not wildcards), max 120 characters |
| `GET`/`PUT`/`DELETE` | `/teams/{id}` | Get / rename / delete a team. Delete returns **409** if the team still has players on its roster |
| `GET`/`POST` | `/players` | List (optionally `?team_id=`) / create players. An unknown `team_id` returns **404** `Team not found` |
| `GET`/`PUT`/`DELETE` | `/players/{id}` | Get / update (an unknown `team_id` is a **404** here too) / delete a player. Delete is always safe (204) — saved lineups are frozen snapshots, so deleting a player never breaks them |
| `GET`/`POST` | `/lineups/saved` | List (optionally `?source_team_id=`) / create saved lineups |
| `GET`/`DELETE` | `/lineups/saved/{id}` | Get / delete a saved lineup |
| `POST` | `/lineups/saved/{id}/generate?format=pdf\|docx` | Generate a PDF/DOCX from a previously saved lineup |

A saved lineup freezes team/opponent names and each player's name/NSSZ number as text at creation time. Team, opponent, and each player can be specified either by referencing an existing record (`source_team_id`, `source_opponent_id`, `source_player_id` — the current name/NSSZ is copied in) or by free text (`team_name`, `opponent_name`, player `name`/`nssz_number`); **exactly one** of the two must be given per field (sending both is a `422`, so it is never ambiguous which value wins). The same NSSZ number can't appear twice in one lineup (`422`), on either endpoint. Once saved, deleting the source team or player has no effect on the lineup.

```json
POST /lineups/saved
{
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
| `task run`      | Run the CLI application                                         |
| `task serve`    | Start the API server locally (DOCX only; loads `backend/.env`; creates tables on startup unless `ENV=production`) |
| `task db:status` | Show whether `backend/.env` currently selects SQLite or the Supabase pooler |
| `task db:postgres` | Switch `backend/.env` to the Supabase pooler (`DATABASE_URL` + `ENV=production`) |
| `task db:sqlite` | Switch `backend/.env` back to local SQLite                             |
| `task test`     | Run tests with coverage (100%)                                  |
| `task test-e2e` | Build+run the container and verify real PDF conversion fidelity |
| `task lint`     | Lint the codebase with ruff                                     |
| `task format`   | Format the codebase with ruff                                   |
| `task build`    | Build the container image                                       |
| `task rebuild`  | Force a fresh container image build (no cache)                  |
| `task up`       | Start the API in a container (detached)                         |
| `task down`     | Stop the container                                              |
| `task migrate`  | Apply Alembic migrations (`upgrade head`)                        |
| `task migrate-new -- -m "description"` | Autogenerate a new Alembic migration          |
| `task migrate-down` | Roll back one migration step                                 |
| `task docs:references` | Regenerate the dependency block in `documentation/References.md` |
| `task docs:check` | Fail if that block is stale (CI runs it)                       |

## Project structure

```
lineup/
├── Taskfile.yml                     # Task runner commands (Python tasks run with dir: backend)
├── compose.yml                      # Docker Compose configuration (reads optional backend/.env)
├── documentation/                   # Source of the GitHub wiki (mirrored by CI; incl. Newcomer-Guide.md, References.md)
├── scripts/                         # Repo tooling: check_docs_touched.sh (docs gate), docs_references.py (References generator)
├── .github/                         # CI workflows, PR template + Dependabot config
├── .claude/                         # Shared Claude Code settings, skills, commands
├── PLAN.md  CLAUDE.md               # Working plan and assistant context
├── frontend/                        # Frontend home (design spec only so far)
└── backend/                         # All Python; the working directory for Python commands
    ├── main.py                          # CLI entry point
    ├── app.py                           # FastAPI application entry point
    ├── pyproject.toml  uv.lock          # Dependencies, ruff/pytest/coverage config
    ├── Dockerfile                       # Container image definition
    ├── .dockerignore                    # Keeps secrets/tests out of the image (build context is backend/)
    ├── .env.example                     # Documents the env vars; copy to git-ignored backend/.env
    ├── alembic.ini                      # Alembic configuration
    ├── alembic/
    │   ├── env.py                       # Async migration environment
    │   └── versions/
    │       └── 35ce55ceabf4_initial_schema.py  # teams/players/saved_lineups/lineup_player_snapshots
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
    │   │   ├── engine.py                # DB engine (SQLite/Postgres aware), get_session() dependency
    │   │   └── models.py                # Team, Player, SavedLineup, LineupPlayerSnapshot
    │   ├── auth/
    │   │   └── dependencies.py          # get_current_user_id() — None pre-Auth
    │   ├── teams/                       # schemas / repository / service / router
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
    │   ├── test_auth_dependencies.py    # Auth dependency unit test
    │   ├── test_db_engine.py            # DB engine unit tests (SQLite pragma gate, Postgres pool settings)
    │   ├── test_db_models.py            # ORM model unit tests
    │   ├── test_teams.py                # Teams API + repository tests
    │   ├── test_players.py              # Players API + repository tests
    │   └── test_saved_lineups.py        # Saved lineups API + repository tests
```

## Customizing the lineup

Edit `backend/main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloLineupDTO` and `Player` classes both use the builder pattern.
