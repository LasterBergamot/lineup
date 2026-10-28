---
paths:
  - "backend/lineup/**"
  - "backend/app.py"
  - "backend/main.py"
---

# Backend: API, modules and OpenAPI conventions

There's also a persistence layer (Teams, Players, Saved Lineups) backed by SQLAlchemy async ORM + Alembic, running on in-memory/file SQLite locally and swappable to Postgres (Supabase) via `DATABASE_URL`. Every data route requires a signed-in user (Supabase JWT, see Auth in the API section below). A team is a *workspace*: access to teams, players and saved lineups is "the caller is a member of the row's team" (`team_members`); `created_by` columns hold the creator's token `sub` for auditing only. See `documentation/Current-State-Backend.md` for the design rationale (snapshot vs. soft-reference strategy, ERD) and `documentation/Roadmap-Backend.md` for the Supabase/OAuth roadmap.

## API

**Auth:** every route needs `Authorization: Bearer <Supabase access token>` (else `401 {"detail":"Not authenticated"}`) except `GET /health`, the API docs and the stateless one-off `POST /lineups` (it starts LibreOffice, so it needs rate limiting / a login before any public deploy: #96). `lineup/auth/dependencies.py:get_current_user_id()` returns a `UUID`, never `None`: `401` for a missing/invalid token, `503` when `SUPABASE_URL` is unset or the signing keys can't be loaded (fail closed). `tests/test_auth_dependencies.py` walks all registered routes and fails if one outside the public list is reachable without a token. Repositories take a *required* user id and join through `team_members` (`teams.repository.member_team_ids(user_id)` is the one building block); there is no skip-the-filter branch. A row of a team you're not in is **404**, never 403 (no existence leak); a *member* without the `owner` role gets 403 on owner-only actions (update/delete team). Setup: `documentation/Auth-Setup.md`.

- `GET /health[?db=1]` — liveness / readiness probe; `200 {"status":"ok"}` or `503 {"status":"unavailable"}`
- `POST /lineups?format=pdf|docx` — fills the template, converts to PDF (or returns DOCX), streams the file back
- `format` query param defaults to `pdf`; `docx` skips LibreOffice conversion entirely
- Request body: `LineupRequest` (match, division, team_name, cap, date, coach, doctor, assistant_coach, team_leader, ball_thrower, players)
- `cap` must be `"Fehér"` or `"Kék"`; players: 1–15, unique cap numbers 1–15
- Returns binary file with `Content-Disposition: attachment` header (`filename=` ASCII fallback + `filename*=UTF-8''…`)
- Errors: 422 invalid input, 503 (+ `Retry-After`) when all PDF conversion slots are busy, 504 LibreOffice timeout, 500 other rendering failures — shared with `POST /lineups/saved/{id}/generate` via `lineup/api/file_response.py`

### Teams / Players / Saved Lineups

- `GET/POST /teams`, `GET/PUT/DELETE /teams/{id}` — CRUD, paginated list of *your* teams (`?limit=&offset=`, `limit` 1–200, default 20; no "all" mode). `TeamResponse` = `id, name, created_by, is_public, created_at, role` (the caller's role: `owner`/`member`). `PUT` (name, optional `is_public` = listed in the opponent directory, unchanged if omitted) and `DELETE` are owner-only. `POST` makes the creator the owner.
- `GET /teams/{id}/opponents/recent?limit=` — distinct `opponent_name`s from the team's own saved lineups, newest first (`limit` 1–50, default 20); members only. Feeds the FE opponent combobox (directory + recent + free text).
- `GET /teams/pool?search=&limit=` — shared opponent pool (sign-in required): public teams (`is_public=True`) only, plain list (not the paginated envelope), `limit` 1–100, `search` is a literal substring (`icontains(..., autoescape=True)`, max 120 chars). Registered **before** `/teams/{id}` in the router so `"pool"` doesn't get swallowed as a `team_id` path param.
- `DELETE /teams/{id}` returns **409** if the team still has roster players (`Player.team_id`) or saved lineups (`SavedLineup.team_id`); otherwise 200. App-level checks, backed by `ON DELETE RESTRICT`.
- `GET/POST /players`, `GET/PUT/DELETE /players/{id}` — CRUD; `team_id` is **required** on create/update (the roster the player sits on; update may move them between your teams) and filterable on list; a `team_id` that is unknown *or* not one of your teams → **404** `Team not found` (checked in `players/service.py` via `team_repo.get_team`, membership-aware). Lists show the players of all your teams. `DELETE /players/{id}` is **unconditionally** safe (204) — it never blocks, because saved lineups store frozen snapshots, not live references.
- `GET/POST /lineups/saved`, `GET/DELETE /lineups/saved/{id}`, `POST /lineups/saved/{id}/generate?format=pdf|docx` — a saved lineup is a frozen snapshot (team/opponent name, per-player name/NSSZ) taken at creation time and lives in a workspace (`team_id`, required, must be your team; list filters `team_id`, `source_team_id`). Team/opponent/player can be supplied either as `source_*_id` (resolved from the live roster at save time, **as the caller**: a team/player of a team you belong to, opponent = such a team or a listed one; foreign ids are 404, never 403) or as free text — **exactly one** of the two per field (`model_validator`s in `lineup/saved_lineups/schemas.py`; sending both is 422, so there is no "free text silently wins"). Duplicate NSSZ numbers in one lineup → 422 (`LineupRequest` validator; `_ensure_unique_nssz` in the saved-lineup service, on the resolved values, case-insensitive). Deleting the source team/player afterwards never changes an already-saved lineup.
- Text input: every string field uses the shared types in `lineup/common/types.py` (`CleanStr50/100/120/200`, `OptionalCleanStr*`): stripped, non-empty, length-capped, and no control characters (`Cc`, surrogates, U+FFFE/FFFF) because python-docx raises on them and tabs/newlines would shift the layout. Optional fields turn a blank into `None`. New text fields must use these types.
- Lists are ordered deterministically (`teams`: name, id; `players`/`saved_lineups`: created_at, id; pool: name, id) and saved-lineup snapshots by cap number (also on the create response: `repository.create_saved_lineup` refreshes the relationship).
- Pagination envelope: `{ "items": [...], "total": ..., "limit": ..., "offset": ... }` for all paginated list endpoints except `/teams/pool`.

## Key modules

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
| `lineup/db/engine.py` | `DATABASE_URL` env var (default `sqlite+aiosqlite:///./lineup.db`); `get_session()` FastAPI dependency; `enable_sqlite_foreign_keys()` (SQLite-only, no-op on other dialects); `_make_engine_kwargs()` (`NullPool` for Postgres) — see `.claude/rules/backend-db.md` |
| `lineup/db/models.py` | `Team`, `TeamMember`, `TeamInvitation`, `Player`, `SavedLineup`, `LineupPlayerSnapshot` (+ `TeamRole`) — see `.claude/rules/backend-db.md` |
| `lineup/auth/dependencies.py`, `lineup/auth/tokens.py` | `get_current_user_id()` (`HTTPBearer`, 401/503) over `verify_token()`: only `ES256`/`RS256`, `kid` lookup in a `JwksCache` (TTL 10 min, refetch on unknown `kid` at most every 30 s, stale keys never used, fetched with async `httpx`), checks `iss`/`aud=authenticated`/`exp`/`nbf` (10 s leeway) and a UUID `sub`. Issuer and JWKS URL derive from `SUPABASE_URL`. Failures log a fixed reason code, never the token |
| `lineup/teams/*.py`, `lineup/players/*.py`, `lineup/saved_lineups/*.py` | Standard `schemas.py`/`repository.py`/`service.py`/`router.py` layering per module |

## OpenAPI / FastAPI conventions

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's query parameter introspection
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to appear in the docs
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI renders enums from `$ref` correctly
- The endpoint is annotated `-> Response` for its raw binary file output — this does **not** suppress query-parameter display; the `format` param still appears in the OpenAPI spec (verified via `/openapi.json`). FastAPI derives query params from the function signature, not the return annotation.
