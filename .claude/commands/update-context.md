Review the current state of the project and update the context and documentation files to reflect any changes.

Steps:
1. Read `CLAUDE.md` (a router: summary, always-on rules, a table pointing at the detail) and `.claude/context/claude-code.md` (which file covers which area).
2. Compare the rule and context files you need against the actual project files, and update `.claude/rules/*.md` and `.claude/context/*.md` if the module list, API shape, container setup, tasks, conventions or workflow changed. Keep `CLAUDE.md` itself under 100 lines.
3. Read `README.md` and update it if any user-facing details have changed: API behaviour, prerequisites, available tasks, or project structure (the only copy of the file tree).
4. Run `task test` (pytest with coverage, run from `backend/`) and confirm all tests pass at 100% coverage. If not, identify and fix the gaps before finishing.
