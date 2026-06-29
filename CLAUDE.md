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
| `lineup/document/pdf_converter.py` | Converts docx bytes → PDF bytes via `libreoffice --headless` subprocess |
| `lineup/water_polo/water_polo_lineup_creator.py` | Orchestrates template filling; exposes `create_document_bytes()` and `create_pdf_bytes()` |
| `lineup/water_polo/water_polo_lineup_dto.py` | `WaterPoloLineupDTO` and `Player` data classes with builder pattern |

### Container

- `Dockerfile`: `python:3.13-slim` + LibreOffice via `apt` + `uv` for deps
- `compose.yml`: single `api` service using the pre-built `lineup` image (not `build: .`)
- `task build` / `task rebuild` builds the image; `task up` / `task down` starts/stops it
- `podman compose` builds a separate `lineup_api` image — always use `task build` first, not `podman compose up` alone

---

## Development Workflow

```
task install   # uv sync — install dependencies
task test      # pytest with coverage (must pass at 100%)
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

### OpenAPI / FastAPI

- Do not use `from __future__ import annotations` in router files — it breaks FastAPI's query parameter introspection
- Query parameters must use `Annotated[..., Query(...)]` with an explicit `Query()` to appear in the docs
- Use `class MyEnum(str, Enum)` instead of `Literal[...]` for query param enums — Swagger UI renders enums from `$ref` correctly
- Do not annotate endpoint return type as `-> Response` — it suppresses query parameter display in the OpenAPI spec

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
    │   └── expected_rajtlista.docx
    ├── conftest.py
    ├── test_api.py
    ├── test_document_manager.py
    ├── test_pdf_converter.py
    ├── test_water_polo_lineup_creator.py
    └── test_water_polo_lineup_dto.py
```
