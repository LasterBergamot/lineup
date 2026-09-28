# lineup

A tool for generating water polo lineup documents. It takes match details and player information, then fills in a `.docx` template (`resources/rajtlista.docx`) and converts the result to a PDF.

The document can be generated via a REST API, which returns the populated file as a PDF. The API also provides CRUD endpoints for managing teams, players, and saved lineups (persisted in SQLite locally, swappable to Postgres in production), so a lineup can be built from a saved roster instead of a one-off request payload.

## AI Assistant

This project uses [Claude Code](https://claude.ai/code) as an AI coding assistant. The `CLAUDE.md` file at the root contains the project context that Claude Code reads automatically at the start of every session. Use `/update-context` to sync `CLAUDE.md` and `README.md` after making changes.

## Prerequisites

- **Operating System:** Any Linux distribution, preferably **Arch Linux**. On Windows, [Try Omarchy for Windows](https://github.com/omacom/try-omarchy-windows) can be used.
- [Python 3.x](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — dependency manager
- [Task](https://taskfile.dev/installation/) — task runner
- [Docker Engine](https://docs.docker.com/engine/) & [Docker Compose](https://docs.docker.com/compose/) — container engine and compose (required for PDF conversion via LibreOffice)
- [lazydocker](https://github.com/jesseduffield/lazydocker) — terminal UI for Docker containers (recommended for container management)

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

Starts the API server at `http://127.0.0.1:8000`. Interactive docs are available at `http://127.0.0.1:8000/docs`. You can monitor and manage containers using [lazydocker](https://github.com/jesseduffield/lazydocker).

### `POST /lineups`

Generates a lineup document from the provided data.

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
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..pdf"

# DOCX
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="rajtlista_SZVTK_2024. 12. 21..docx"
```

### Teams, Players & Saved Lineups

Backed by a SQLite database (in-memory for tests, file-backed at `./lineup.db` for local dev via `task serve`, swappable to Postgres via `DATABASE_URL`). All list endpoints are paginated: `?limit=20&offset=0`, where `limit=0` returns everything, in the envelope `{ "items": [...], "total": ..., "limit": ..., "offset": ... }`.

| Method | Path | Description |
|--------|------|--------------|
| `GET`/`POST` | `/teams` | List / create teams |
| `GET` | `/teams/pool?search=&limit=` | Search the shared pool of public teams (for opponent selection) — plain list, not paginated |
| `GET`/`PUT`/`DELETE` | `/teams/{id}` | Get / rename / delete a team. Delete returns **409** if the team still has players on its roster |
| `GET`/`POST` | `/players` | List (optionally `?team_id=`) / create players |
| `GET`/`PUT`/`DELETE` | `/players/{id}` | Get / update / delete a player. Delete is always safe (204) — saved lineups are frozen snapshots, so deleting a player never breaks them |
| `GET`/`POST` | `/lineups/saved` | List (optionally `?source_team_id=`) / create saved lineups |
| `GET`/`DELETE` | `/lineups/saved/{id}` | Get / delete a saved lineup |
| `POST` | `/lineups/saved/{id}/generate?format=pdf\|docx` | Generate a PDF/DOCX from a previously saved lineup |

A saved lineup freezes team/opponent names and each player's name/NSSZ number as text at creation time. Team, opponent, and each player can be specified either by referencing an existing record (`source_team_id`, `source_opponent_id`, `source_player_id` — the current name/NSSZ is copied in) or by free text (`team_name`, `opponent_name`, player `name`/`nssz_number`); at least one of the two must be given per field. Once saved, deleting the source team or player has no effect on the lineup.

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
| `task serve`    | Start the API server locally                                    |
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

## Project structure

```
lineup/
├── main.py                          # CLI entry point
├── app.py                           # FastAPI application entry point
├── Dockerfile                       # Container image definition
├── compose.yml                      # Docker Compose configuration
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
│   │   └── router.py                # POST /lineups endpoint
│   ├── document/
│   │   ├── document_manager.py      # .docx read/write logic
│   │   └── pdf_converter.py         # docx → PDF via LibreOffice
│   ├── water_polo/
│   │   ├── water_polo_lineup_creator.py  # Orchestrates document generation
│   │   └── water_polo_lineup_dto.py      # Data model and builders
│   ├── db/
│   │   ├── base.py                  # DeclarativeBase
│   │   ├── engine.py                # DB engine, get_session() dependency
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
│   ├── test_document_manager.py     # DocumentManager unit tests
│   ├── test_pdf_converter.py        # PdfConverter unit tests
│   ├── test_pdf_conversion_e2e.py   # Real-conversion fidelity tests (container)
│   ├── test_water_polo_lineup_creator.py  # Creator unit tests
│   ├── test_water_polo_lineup_dto.py      # DTO and builder unit tests
│   ├── test_auth_dependencies.py    # Auth dependency unit test
│   ├── test_db_engine.py            # DB engine unit test
│   ├── test_teams.py                # Teams API + repository tests
│   ├── test_players.py              # Players API + repository tests
│   └── test_saved_lineups.py        # Saved lineups API + repository tests
└── Taskfile.yml
```

## Customizing the lineup

Edit `main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloLineupDTO` and `Player` classes both use the builder pattern.
