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

---

## Architecture

### API

- `POST /lineups?format=pdf|docx` — fills the template, converts to PDF (or returns DOCX), streams the file back
- `format` query param defaults to `pdf`; `docx` skips LibreOffice conversion entirely
- Request body: `LineupRequest` (match, division, team_name, cap, date, coach, doctor, assistant_coach, team_leader, ball_thrower, players)
- `cap` must be `"Fehér"` or `"Kék"`; players: 1–15, unique cap numbers 1–15
- Returns binary file with `Content-Disposition: attachment` header

### Key modules

| File | Responsibility |
|------|---------------|
| `app.py` | FastAPI app entry point |
| `main.py` | CLI entry point |
| `lineup/api/models.py` | Pydantic request models (`LineupRequest`, `PlayerRequest`) |
| `lineup/api/router.py` | `POST /lineups` endpoint; `FileFormat` enum for the `format` query param |
| `lineup/document/document_manager.py` | `.docx` read/write/style logic |
| `lineup/document/pdf_converter.py` | Converts docx bytes → PDF bytes via `libreoffice --headless` subprocess; uses a private per-call `-env:UserInstallation` profile and a 120s timeout (`CONVERSION_TIMEOUT_SECONDS`) |
| `lineup/water_polo/water_polo_lineup_creator.py` | Orchestrates template filling; exposes `create_document_bytes()` and `create_pdf_bytes()` |
| `lineup/water_polo/water_polo_lineup_dto.py` | `WaterPoloLineupDTO` and `Player` data classes with builder pattern |

### Container

- `Dockerfile`: `python:3.13-slim` + LibreOffice via `apt` + `uv` for deps
- Fonts: `--no-install-recommends` is kept, so the metric-compatible font packages are installed explicitly — `fonts-crosextra-carlito` (Calibri/Calibri Light), `fonts-crosextra-caladea` (Cambria), `fonts-liberation2` (Arial/Times/Courier). `docker/fontconfig/99-calibri-carlito.conf` (copied to `/etc/fonts/conf.d/`) forces Calibri → Carlito, and `fc-cache -f` refreshes the cache. These are what make the PDF match the source `.docx`.
- `.dockerignore` keeps the build context lean and, notably, excludes `tests/` (plus `.venv/`, `.claude/`, `.coverage`) — so the image ships without tests. That's why the e2e suite runs from the host against the running container, not inside the image.
- `compose.yml`: single `api` service using the pre-built `lineup` image (not `build: .`)
- `task build` / `task rebuild` builds the image; `task up` / `task down` starts/stops it
- `podman compose` builds a separate `lineup_api` image — always use `task build` first, not `podman compose up` alone

---

## Development Workflow

```
task install   # uv sync — install dependencies
task test      # pytest with coverage (must pass at 100%; e2e tests excluded)
task test-e2e  # build image, start container, run real-conversion fidelity tests, tear down
task lint      # ruff check
task format    # ruff format
task serve     # local uvicorn dev server (no PDF support — no LibreOffice)
task build     # build container image (localhost/lineup)
task rebuild   # force fresh build with --no-cache
task up        # start container in detached mode
task down      # stop container
```

---

## Conventions

### Tests

- `pyproject.toml` enforces `fail_under = 100`
- Every new module needs a corresponding `tests/test_<module>.py`
- Any code that calls LibreOffice must mock `PdfConverter.convert` — it is not available locally
- Tests for API endpoints that trigger PDF conversion use an `autouse` fixture in `test_api.py` that patches `PdfConverter.convert`
- `tests/test_pdf_conversion_e2e.py` is the exception: it drives the **real** conversion against the running container. It is marked `e2e` and excluded from `task test` by `addopts = "-m 'not e2e'"` (so it never affects coverage); run it via `task test-e2e`. It talks to the API over HTTP (stdlib `urllib`) and validates layout with `pdfplumber` — asserting a single page, expected text, and that word widths/positions match `expected-rajtlista.pdf`. It does **not** pixel-diff (the reference uses real Calibri, the container uses metric-compatible Carlito).

### OpenAPI / FastAPI

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's query parameter introspection
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to appear in the docs
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI renders enums from `$ref` correctly
- The endpoint is annotated `-> Response` for its raw binary file output — this does **not** suppress query-parameter display; the `format` param still appears in the OpenAPI spec (verified via `/openapi.json`). FastAPI derives query params from the function signature, not the return annotation.

### Container image

- `compose.yml` uses `image: lineup`, not `build: .` — so `task build`/`task rebuild` is always needed before `task up`
- To fully reset: `task down` → `podman rmi lineup lineup_api` → `podman image prune` → `task rebuild` → `task up`

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
├── lineup/
│   ├── api/
│   │   ├── models.py
│   │   └── router.py
│   ├── document/
│   │   ├── document_manager.py
│   │   └── pdf_converter.py
│   └── water_polo/
│       ├── water_polo_lineup_creator.py
│       └── water_polo_lineup_dto.py
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
    └── test_water_polo_lineup_dto.py
```
