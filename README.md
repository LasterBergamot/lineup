# lineup

A tool for generating water polo lineup documents. It takes match details and player information, then fills in a `.docx` template (`resources/rajtlista.docx`) and saves the result as `resources/modified_rajtlista.docx`.

The same document can also be generated via a REST API, which returns the populated file as a Base64-encoded response.

## Prerequisites

- [Python 3.x](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — dependency manager
- [Task](https://taskfile.dev/installation/) — task runner

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

```bash
task serve
```

Starts the API server at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs`.

### `POST /lineups`

Generates a lineup document from the provided data.

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

```json
{
  "document": "<base64-encoded .docx>",
  "filename": "rajtlista_SZVTK_2024. 12. 21..docx"
}
```

## Available tasks

| Task           | Description                        |
|----------------|------------------------------------|
| `task install` | Install dependencies via `uv sync` |
| `task run`     | Run the CLI application            |
| `task serve`   | Start the API server               |
| `task test`    | Run tests with coverage (≥80%)     |
| `task lint`    | Lint the codebase with ruff        |
| `task format`  | Format the codebase with ruff      |

## Project structure

```
lineup/
├── main.py                          # CLI entry point
├── app.py                           # FastAPI application entry point
├── resources/
│   └── rajtlista.docx               # Input document template
├── lineup/
│   ├── api/
│   │   ├── models.py                # Pydantic request/response models
│   │   └── router.py                # POST /lineups endpoint
│   ├── document/
│   │   └── document_manager.py      # .docx read/write logic
│   └── water_polo/
│       ├── water_polo_lineup_creator.py  # Orchestrates document generation
│       └── water_polo_lineup_dto.py      # Data model and builders
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── test_api.py                  # API endpoint tests
│   ├── test_document_manager.py     # DocumentManager unit tests
│   └── test_water_polo_lineup_creator.py  # Creator unit tests
└── Taskfile.yml
```

## Customizing the lineup

Edit `main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloLineupDTO` and `Player` classes both use the builder pattern.
