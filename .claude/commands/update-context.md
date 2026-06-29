Review the current state of the project and update the context and documentation files to reflect any changes.

Steps:
1. Read `CLAUDE.md` and compare it against the actual project files.
2. Update `CLAUDE.md` if any of the following have changed: module list, API shape, container setup, tasks, conventions, or project structure.
3. Read `README.md` and update it if any user-facing details have changed: API behaviour, prerequisites, available tasks, or project structure.
4. Run `uv run pytest --cov=lineup --cov-report=term-missing` and confirm all tests pass at 100% coverage. If not, identify and fix the gaps before finishing.
