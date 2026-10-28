---
paths:
  - "backend/tests/**"
---

# Backend: test conventions

Paths below are relative to `backend/` (run pytest from there — `task test` does).

- `pyproject.toml` enforces `fail_under = 100`
- Every new module needs a corresponding `tests/test_<module>.py`
- Any code that calls LibreOffice must mock `PdfConverter.convert` — it is not available locally. `tests/test_pdf_converter.py` mocks `subprocess.Popen` (and `shutil.which`); its one real-process test uses a fake `libreoffice` shell script that forks a child, to prove the group kill reaches it (Linux `/proc` only)
- Tests for API endpoints that trigger PDF conversion use an `autouse` fixture in `test_api.py` (and in `TestGenerateFromSavedLineup` in `test_saved_lineups.py`) that patches `PdfConverter.convert`. To force a rendering failure, patch `lineup.api.file_response.WaterPoloLineupCreator` — that's where both endpoints construct it now
- `tests/test_pdf_conversion_e2e.py` is the exception: it drives the **real** conversion against the running container. It is marked `e2e` and excluded from `task test` by `addopts = "-m 'not e2e'"` (so it never affects coverage); run it via `task test-e2e`. It talks to the API over HTTP (stdlib `urllib`) and validates layout with `pdfplumber` — asserting a single page, expected text, and that word widths/positions match `expected-rajtlista.pdf`. It does **not** pixel-diff (the reference uses real Calibri, the container uses metric-compatible Carlito).
- DB tests use the `async_client` fixture (`tests/conftest.py`) — a fresh in-memory SQLite DB per test, with `get_session` and `get_current_user_id` dependency-overridden to the `current_user` fixture's id (assign `current_user.id = uuid.uuid4()` mid-test to act as a second user). `tests/test_tenant_isolation.py` uses that to prove one user can't reach another's rows (404) and teammates share theirs (`TeamMember` rows added directly, there is no invitation endpoint yet); the repository tests also call the user-scoped functions directly with real ids. `tests/helpers.py` (`ensure_team`, `create_player`) gives tests the team that players and lineups must live in.
- `tests/test_auth_dependencies.py` tests the real token check with throw-away keys generated in the test (ES256 and RS256), a fake JWKS fetch function and a fake clock: no network, no Supabase. Keep it that way.
- `[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet", "thread"]` — required for accurate coverage of any code that calls SQLAlchemy's async ORM. Don't remove it; without it, coverage under-reports on lines following an `await session.commit()`/`.refresh()`/etc. even though they actually ran.
- `tests/test_postgres_migrations.py` asserts RLS/role/grant behaviour against a real Postgres; it is **skipped** unless `POSTGRES_TEST_URL` is set (a throwaway, empty DB — CI's `Migrations (Postgres)` job sets it; locally run a `postgres:17` container). `tests/test_app_role.py` covers the password/`.env` rewriting with a fake engine (no DB).
- `tests/test_app.py` covers both branches of `app.py`'s Sentry init (`SENTRY_DSN` set/unset) by mocking `sentry_sdk.init` and `importlib.reload`-ing the `app` module under each env state. Safe to reload freely: `tests/conftest.py` imports `app` once at collection time and keeps its own reference, so a later reload elsewhere doesn't retroactively affect the `client`/`async_client` fixtures. Note `[tool.coverage.run] source = ["lineup"]` doesn't include `app.py`, so this file's coverage isn't actually gated by `fail_under = 100` — the tests exist for correctness, not the coverage requirement.
