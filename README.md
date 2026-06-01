# lineup

A tool for generating water polo start list documents. It takes match details and player information, then fills in a `.docx` template (`resources/rajtlista.docx`) and saves the result as `resources/modified_rajtlista.docx`.

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

## Available tasks

| Task           | Description                        |
|----------------|------------------------------------|
| `task install` | Install dependencies via `uv sync` |
| `task run`     | Run the application                |
| `task lint`    | Lint the codebase with ruff        |
| `task format`  | Format the codebase with ruff      |

## Project structure

```
lineup/
├── main.py                          # Entry point
├── resources/
│   └── rajtlista.docx               # Input document template
├── lineup/
│   ├── document/
│   │   └── document_manager.py      # .docx read/write logic
│   └── water_polo/
│       ├── water_polo_start_list_creator.py  # Orchestrates document generation
│       └── water_polo_start_list_dto.py      # Data model and builders
└── Taskfile.yml
```

## Customizing the start list

Edit `main.py` to set match details (teams, division, date, staff) and player data (name, cap number, NSSZ registration number). The `WaterPoloStartListDTO` and `Player` classes both use the builder pattern.
