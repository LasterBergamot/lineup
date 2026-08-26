# lineup

A tool for generating water polo lineup documents. It takes match details and player information, then fills in a `.docx` template (`resources/rajtlista.docx`) and converts the result to a PDF.

The document can be generated via a REST API, which returns the populated file as a PDF.

## AI Assistant

This project uses [Claude Code](https://claude.ai/code) as an AI coding assistant. The `CLAUDE.md` file at the root contains the project context that Claude Code reads automatically at the start of every session. Use `/update-context` to sync `CLAUDE.md` and `README.md` after making changes.

## Prerequisites

- [Python 3.x](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — dependency manager
- [Task](https://taskfile.dev/installation/) — task runner
- [Podman Desktop](https://podman-desktop.io/) — container engine (required for PDF conversion via LibreOffice)
- [podman-compose](https://github.com/containers/podman-compose) — Compose support for Podman (`uv tool install podman-compose`)

## Installation

```bash
task install
```

This runs `uv sync` and sets up the virtual environment with all required dependencies.

## Running

```bash
task run
```

The output document is written to `resources/modified_rajtlista.docx`.

## API

The API runs inside a container so that LibreOffice is available for PDF conversion. The
image also bundles the libre, metric-compatible fonts (Carlito for Calibri, etc.) that the
template relies on, so the generated PDF matches the source `.docx` layout.

```bash
task build
task up
```

Starts the API server at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs`.

### `POST /lineups`

Generates a lineup document from the provided data.

**Query parameters:**

| Parameter | Values         | Default | Description                        |
|-----------|----------------|---------|------------------------------------|
| `format`  | `pdf`, `docx`  | `pdf`   | Output format of the generated file |

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
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..pdf"

# DOCX
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..docx"
```

## Available tasks

| Task           | Description                         |
|----------------|-------------------------------------|
| `task install` | Install dependencies via `uv sync`  |
| `task run`     | Run the CLI application             |
| `task serve`   | Start the API server locally        |
| `task test`    | Run tests with coverage (100%)      |
| `task test-e2e`| Build+run the container and verify real PDF conversion fidelity |
| `task lint`    | Lint the codebase with ruff         |
| `task format`  | Format the codebase with ruff       |
| `task build`   | Build the container image                    |
| `task rebuild` | Force a fresh container image build (no cache) |
| `task up`      | Start the API in a container (detached)      |
| `task down`    | Stop the container                           |

## Project structure

```
lineup/
├── main.py                          # CLI entry point
├── app.py                           # FastAPI application entry point
├── Dockerfile                       # Container image definition
├── compose.yml                      # Podman Compose configuration
├── docker/
│   └── fontconfig/
│       └── 99-calibri-carlito.conf  # Calibri → Carlito font mapping (copied into image)
├── resources/
│   └── rajtlista.docx               # Input document template
├── lineup/
│   ├── api/
│   │   ├── models.py                # Pydantic request models
│   │   └── router.py                # POST /lineups endpoint
│   ├── document/
│   │   ├── document_manager.py      # .docx read/write logic
│   │   └── pdf_converter.py         # docx → PDF via LibreOffice
│   └── water_polo/
│       ├── water_polo_lineup_creator.py  # Orchestrates document generation
│       └── water_polo_lineup_dto.py      # Data model and builders
├── tests/
│   ├── resources/
│   │   ├── expected_rajtlista.docx  # Test fixture
│   │   └── expected-rajtlista.pdf   # Reference render for the e2e fidelity test
│   ├── conftest.py                  # Shared fixtures
│   ├── test_api.py                  # API endpoint tests
│   ├── test_document_manager.py     # DocumentManager unit tests
│   ├── test_pdf_converter.py        # PdfConverter unit tests
│   ├── test_pdf_conversion_e2e.py   # Real-conversion fidelity tests (container)
│   ├── test_water_polo_lineup_creator.py  # Creator unit tests
│   └── test_water_polo_lineup_dto.py      # DTO and builder unit tests
└── Taskfile.yml
```

## Customizing the lineup

Edit `main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloLineupDTO` and `Player` classes both use the builder pattern.
