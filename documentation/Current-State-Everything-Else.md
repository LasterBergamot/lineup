# Current State: Everything Else

Cross-cutting concerns: dev workflow, containerization, testing, and conventions that apply
across the backend regardless of which module you're touching.

## Dev workflow (`Taskfile.yml`)

| Task | Purpose |
|---|---|
| `task install` | `uv sync` — install dependencies |
| `task test` | pytest with coverage (must pass at 100%; e2e tests excluded) |
| `task test-e2e` | build image, start container, run real-conversion fidelity tests, tear down |
| `task lint` / `task format` | `ruff check` / `ruff format` |
| `task serve` | local uvicorn dev server (no PDF support — no LibreOffice locally; DB tables auto-created on startup) |
| `task build` / `task rebuild` | build container image (`localhost/lineup`) / force fresh build with `--no-cache` |
| `task up` / `task down` | start/stop the container |
| `task migrate` / `task migrate-new -- -m "..."` / `task migrate-down` | Alembic upgrade / autogenerate / rollback one step |

## Containerization

- `Dockerfile`: `python:3.13-slim` + LibreOffice via `apt` + `uv` for deps.
- **Font fidelity**: the template is authored in Calibri/Calibri Light (proprietary).
  `--no-install-recommends` is kept, so the metric-compatible substitutes are installed
  explicitly: `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea`
  (Cambria), `fonts-liberation2` (Arial/Times/Courier).
  `docker/fontconfig/99-calibri-carlito.conf` forces Calibri → Carlito and `fc-cache -f`
  refreshes the cache — without this, LibreOffice substitutes a differently-sized font and
  the tab-stop/table layout drifts in the PDF.
- `.dockerignore` excludes `tests/` (plus `.venv/`, `.claude/`, `.coverage`) to keep the
  image lean — the image ships without tests, which is why the e2e suite runs from the host
  against the running container rather than inside the image.
- `compose.yml` uses `image: lineup` (not `build: .`), so `task build`/`task rebuild` is
  always required before `task up`. Full reset: `task down` → `docker rmi lineup` →
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
  DB per test, with `get_session` and `get_current_user_id` dependency-overridden.
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
