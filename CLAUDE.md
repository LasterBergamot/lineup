# Lineup — Claude Code Project Context

## Instructions

- Read this file at the start of every session before doing anything.
- After completing any task: update this file if architecture, conventions, tasks, or modules changed.
- After any user-facing change: update `README.md` (API changes, new tasks, new prerequisites, structure changes).
- For any new code: write tests. For changed code: update existing tests. Coverage must stay at 100%.

---

## Project Overview

Water polo lineup document generator. Takes match details and player info, fills a `.docx` template (`resources/rajtlista.docx`), and returns the result via a REST API as either a PDF (default) or DOCX.

PDF conversion uses LibreOffice headless, which is only available inside the container — the API must be run via `task build` + `task up`, not `task serve`.

The template is authored in Calibri/Calibri Light (proprietary). The container ships the libre metric-compatible substitutes (Carlito etc.) so the PDF layout matches the source `.docx`; without them LibreOffice substitutes a differently-sized font and the tab-stop/table layout drifts.

There's also a persistence layer (Teams, Players, Saved Lineups) backed by SQLAlchemy async ORM + Alembic, running on in-memory/file SQLite locally and swappable to Postgres via `DATABASE_URL`. It's pre-Auth: `user_id`/`owner_id` columns exist everywhere but always resolve to `None` until real auth is wired in. See `in-memory-db-plan.md` for the full design rationale (snapshot vs. soft-reference strategy, ERD, Supabase/OAuth roadmap) — that file is a living document, not a historical record.

---

## Architecture

### API

- `POST /lineups?format=pdf|docx` — fills the template, converts to PDF (or returns DOCX), streams the file back
- `format` query param defaults to `pdf`; `docx` skips LibreOffice conversion entirely
- Request body: `LineupRequest` (match, division, team_name, cap, date, coach, doctor, assistant_coach, team_leader, ball_thrower, players)
- `cap` must be `"Fehér"` or `"Kék"`; players: 1–15, unique cap numbers 1–15
- Returns binary file with `Content-Disposition: attachment` header

#### Teams / Players / Saved Lineups

- `GET/POST /teams`, `GET/PUT/DELETE /teams/{id}` — CRUD, paginated list (`?limit=&offset=`, `limit=0` = all)
- `GET /teams/pool?search=&limit=` — shared opponent pool: public teams (`is_public=True`) only, plain list (not the paginated envelope). Registered **before** `/teams/{id}` in the router so `"pool"` doesn't get swallowed as a `team_id` path param.
- `DELETE /teams/{id}` returns **409** if the team still has roster players assigned (`Player.team_id`); otherwise 200. This check is app-level, not DB-level.
- `GET/POST /players`, `GET/PUT/DELETE /players/{id}` — CRUD; `team_id` is optional on create/update and filterable on list. `DELETE /players/{id}` is **unconditionally** safe (204) — it never blocks, because saved lineups store frozen snapshots, not live references.
- `GET/POST /lineups/saved`, `GET/DELETE /lineups/saved/{id}`, `POST /lineups/saved/{id}/generate?format=pdf|docx` — a saved lineup is a frozen snapshot (team/opponent name, per-player name/NSSZ) taken at creation time. Team/opponent/player can be supplied either as `source_*_id` (resolved from the live roster at save time) or as free text — at least one of the two is required per field (enforced by Pydantic `model_validator`s in `lineup/saved_lineups/schemas.py`). Deleting the source team/player afterwards never changes an already-saved lineup.
- Pagination envelope: `{ "items": [...], "total": ..., "limit": ..., "offset": ... }` for all paginated list endpoints except `/teams/pool`.

### Key modules

| File | Responsibility |
|------|---------------|
| `app.py` | FastAPI app entry point; lifespan calls `Base.metadata.create_all` unless `ENV=production` (Alembic handles DDL in prod); registers all 4 routers |
| `main.py` | CLI entry point |
| `lineup/api/models.py` | Pydantic request models (`LineupRequest`, `PlayerRequest`) |
| `lineup/api/router.py` | `POST /lineups` endpoint; `FileFormat` enum for the `format` query param |
| `lineup/document/document_manager.py` | `.docx` read/write/style logic |
| `lineup/document/pdf_converter.py` | Converts docx bytes → PDF bytes via `libreoffice --headless` subprocess; uses a private per-call `-env:UserInstallation` profile and a 120s timeout (`CONVERSION_TIMEOUT_SECONDS`) |
| `lineup/water_polo/water_polo_lineup_creator.py` | Orchestrates template filling; exposes `create_document_bytes()` and `create_pdf_bytes()` |
| `lineup/water_polo/water_polo_lineup_dto.py` | `WaterPoloLineupDTO` and `Player` data classes with builder pattern |
| `lineup/db/engine.py` | `DATABASE_URL` env var (default `sqlite+aiosqlite:///./lineup.db`); `get_session()` FastAPI dependency; `enable_sqlite_foreign_keys()` — see note below |
| `lineup/db/models.py` | `Team`, `Player`, `SavedLineup`, `LineupPlayerSnapshot` — see Data model note below |
| `lineup/auth/dependencies.py` | `get_current_user_id()` — always returns `None` pre-Auth; post-Auth, replace its body to extract the JWT `sub` claim, zero router/service changes needed |
| `lineup/teams/*.py`, `lineup/players/*.py`, `lineup/saved_lineups/*.py` | Standard `schemas.py`/`repository.py`/`service.py`/`router.py` layering per module |

**Data model** (see `in-memory-db-plan.md` for the full ERD and rationale): `Team.players` and `SavedLineup.player_snapshots` are `relationship(..., lazy="selectin")` — async SQLAlchemy can't lazy-load relationships synchronously (raises `MissingGreenlet`), so eager `selectin` loading is required. A `SavedLineup` freezes `team_name`/`opponent_name`/`match_name` as plain text plus nullable soft FKs `source_team_id`/`source_opponent_id` → `teams.id` (`ondelete="SET NULL"`); each `LineupPlayerSnapshot` freezes `name`/`nssz_number`/`cap_number` plus a nullable soft FK `source_player_id` → `players.id` (`ondelete="SET NULL"`). `Player.team_id` → `teams.id` uses `ondelete="RESTRICT"` at the DB level, but team deletion is actually blocked earlier, at the service layer (409), so the DB-level RESTRICT never fires in practice.

**SQLite foreign key enforcement**: SQLite ignores `ondelete` clauses entirely unless `PRAGMA foreign_keys=ON` is set per-connection — `enable_sqlite_foreign_keys(engine)` in `lineup/db/engine.py` registers a SQLAlchemy `connect` event listener that sets this pragma; both the production engine and the test engine (`tests/conftest.py`'s `db_engine` fixture) call it. Without it, `SET NULL`/`RESTRICT` are silently inert.

**Coverage + async SQLAlchemy gotcha**: `coverage.py` needs `concurrency = ["greenlet", "thread"]` under `[tool.coverage.run]` in `pyproject.toml` — SQLAlchemy's async ORM bridges sync calls onto greenlets (`greenlet_spawn`), and without this setting, `coverage` silently drops line hits for code *after* a greenlet-based await resumes (e.g. the line right after `await session.commit()`), even though the code genuinely ran. This looked like a real ~90%-coverage shortfall across every DB-touching module until traced to this missing config.

### Container

- `Dockerfile`: `python:3.13-slim` + LibreOffice via `apt` + `uv` for deps
- Fonts: `--no-install-recommends` is kept, so the metric-compatible font packages are installed explicitly — `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea` (Cambria), `fonts-liberation2` (Arial/Times/Courier). `docker/fontconfig/99-calibri-carlito.conf` (copied to `/etc/fonts/conf.d/`) forces Calibri → Carlito, and `fc-cache -f` refreshes the cache. These are what make the PDF match the source `.docx`.
- `.dockerignore` keeps the build context lean and, notably, excludes `tests/` (plus `.venv/`, `.claude/`, `.coverage`) — so the image ships without tests. That's why the e2e suite runs from the host against the running container, not inside the image.
- `compose.yml`: single `api` service using the pre-built `lineup` image (not `build: .`)
- `task build` / `task rebuild` builds the image; `task up` / `task down` starts/stops it; containers can be monitored using `lazydocker`

---

## Development Workflow

```
task install    # uv sync — install dependencies
task test       # pytest with coverage (must pass at 100%; e2e tests excluded)
task test-e2e   # build image, start container, run real-conversion fidelity tests, tear down
task lint       # ruff check
task format     # ruff format
task serve      # local uvicorn dev server (no PDF support — no LibreOffice; DB tables auto-created on startup)
task build      # build container image (localhost/lineup)
task rebuild    # force fresh build with --no-cache
task up         # start container in detached mode
task down       # stop container
task migrate    # apply Alembic migrations (upgrade head)
task migrate-new -- -m "description"  # autogenerate a new migration
task migrate-down  # rollback one migration step
```

---

## Conventions

### Tests

- `pyproject.toml` enforces `fail_under = 100`
- Every new module needs a corresponding `tests/test_<module>.py`
- Any code that calls LibreOffice must mock `PdfConverter.convert` — it is not available locally
- Tests for API endpoints that trigger PDF conversion use an `autouse` fixture in `test_api.py` that patches `PdfConverter.convert`
- `tests/test_pdf_conversion_e2e.py` is the exception: it drives the **real** conversion against the running container. It is marked `e2e` and excluded from `task test` by `addopts = "-m 'not e2e'"` (so it never affects coverage); run it via `task test-e2e`. It talks to the API over HTTP (stdlib `urllib`) and validates layout with `pdfplumber` — asserting a single page, expected text, and that word widths/positions match `expected-rajtlista.pdf`. It does **not** pixel-diff (the reference uses real Calibri, the container uses metric-compatible Carlito).
- DB tests use the `async_client` fixture (`tests/conftest.py`) — a fresh in-memory SQLite DB per test, with `get_session` and `get_current_user_id` dependency-overridden (`get_current_user_id` always yields `None`, matching pre-Auth production behavior).
- The `owner_id`/`user_id`-scoped filtering branches in `teams/players/saved_lineups` repositories can't be reached through the API yet (since `get_current_user_id()` always returns `None`) — they're tested directly against the `db_session` fixture instead, calling repository functions with real non-`None` IDs.
- `[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet", "thread"]` — required for accurate coverage of any code that calls SQLAlchemy's async ORM. Don't remove it; without it, coverage under-reports on lines following an `await session.commit()`/`.refresh()`/etc. even though they actually ran.

### OpenAPI / FastAPI

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's query parameter introspection
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to appear in the docs
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI renders enums from `$ref` correctly
- The endpoint is annotated `-> Response` for its raw binary file output — this does **not** suppress query-parameter display; the `format` param still appears in the OpenAPI spec (verified via `/openapi.json`). FastAPI derives query params from the function signature, not the return annotation.

### Container image

- `compose.yml` uses `image: lineup`, not `build: .` — so `task build`/`task rebuild` is always needed before `task up`
- To fully reset: `task down` → `docker rmi lineup` → `docker image prune` → `task rebuild` → `task up`

---

## Project Structure

```
lineup/
├── app.py
├── main.py
├── Dockerfile
├── compose.yml
├── Taskfile.yml
├── docker/
│   └── fontconfig/
│       └── 99-calibri-carlito.conf   # Calibri → Carlito mapping, copied into the image
├── resources/
│   └── rajtlista.docx
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 35ce55ceabf4_initial_schema.py   # single squashed migration — teams/players/saved_lineups/lineup_player_snapshots
├── lineup/
│   ├── api/
│   │   ├── models.py
│   │   └── router.py
│   ├── document/
│   │   ├── document_manager.py
│   │   └── pdf_converter.py
│   ├── water_polo/
│   │   ├── water_polo_lineup_creator.py
│   │   └── water_polo_lineup_dto.py
│   ├── db/
│   │   ├── base.py       # DeclarativeBase
│   │   ├── engine.py     # get_session(), enable_sqlite_foreign_keys()
│   │   └── models.py     # Team, Player, SavedLineup, LineupPlayerSnapshot
│   ├── auth/
│   │   └── dependencies.py   # get_current_user_id() — None pre-Auth
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
    ├── test_document_manager.py
    ├── test_pdf_converter.py
    ├── test_pdf_conversion_e2e.py     # e2e: real conversion vs the running container
    ├── test_water_polo_lineup_creator.py
    ├── test_water_polo_lineup_dto.py
    ├── test_auth_dependencies.py
    ├── test_db_engine.py
    ├── test_teams.py
    ├── test_players.py
    └── test_saved_lineups.py
```
