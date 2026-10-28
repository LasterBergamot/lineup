# Claude Code setup: context layout and skills

## How the project context is organised

`CLAUDE.md` is a router, so a session only carries what it needs:

| Where | Loaded | Holds |
|-------|--------|-------|
| `CLAUDE.md` | at session start | what the project is, the always-on rules, the router table |
| `.claude/rules/*.md` | when Claude reads or edits a file that matches the `paths:` globs in the file's frontmatter | the detail for one area (conventions, gotchas, module tables) |
| `.claude/context/*.md` | only when you (or a skill) read it | workflow, the pre-PR checklist, this file |

Things to know when you add to it:

- A rule file **without** `paths:` loads at session start like `CLAUDE.md`, which defeats the point; always give it `paths:`.
- `@file` imports are expanded eagerly, so they save nothing; the router names files instead.
- The built-in Explore and Plan subagents load neither `CLAUDE.md` nor the rules: name the rule file in their prompt.
- Globs are relative to the repo root and quoted in the frontmatter. `tests/test_docs_tooling.py` fails when a glob matches nothing, when a path the router names doesn't exist, or when `CLAUDE.md` grows past 100 lines.

Which file to update when you change something (`update-documentation` and the docs gate use the same map):

| You changed | Update |
|-------------|--------|
| API, auth, modules, OpenAPI conventions (`backend/lineup/**`, `backend/app.py`) | `.claude/rules/backend-api.md` |
| data model, migrations, engine, Postgres/Supabase notes | `.claude/rules/backend-db.md` |
| test conventions or fixtures | `.claude/rules/backend-tests.md` |
| ruff `S` ignores, `backend/pyproject.toml` lint config | `.claude/rules/backend-security.md` |
| `Dockerfile`, fonts, `compose.yml` | `.claude/rules/container.md` |
| anything in `frontend/` | `.claude/rules/frontend.md` |
| docs rules, wiki pages | `.claude/rules/documentation.md` |
| tasks, environment variables, branches, merge rules | `.claude/context/workflow.md` |
| the Dependabot rule | `.claude/context/pr-checklist.md` |
| skills, settings, this layout | this file |
| the project summary, repo layout, always-on rules | `CLAUDE.md` (keep it short) |

The file tree lives only in `README.md` ("Project structure").

## Skills (`.claude/skills/`)

`repo-audit` (opus): full audit → GitHub reconciliation. `compliance-audit` (opus): GDPR/Hungarian/OWASP checks against its `requirements.md`; full audit → compliance matrix → issues, or `quick <issue#|branch>` per feature (run at issue start and as a `create-pr` gate). `new-issue` (haiku): issue conventions, labels/milestone/board/relations recipes. `triage-dependabot` (sonnet): the pre-PR Dependabot rule in `pr-checklist.md`. `create-pr` (sonnet): gates + PR. `supabase-smoke` (haiku): the live dev-Supabase smoke test (authenticates through `scripts/smoke_auth.py`, a localhost stand-in for Supabase Auth, so no real sign-in is needed). Also `update-documentation` and `setup-project`. The models are pinned with `model:` in each skill's frontmatter and apply only while the skill runs. If you change a workflow these skills encode (labels, milestones, epics, board fields, the Dependabot rule, the smoke-test steps), update the skill in the same change. `.claude/settings.json` (shared) allows `task lint`/`task test` and denies reading `.env*` at the root and `backend/.env*`; `.claude/settings.local.json` is personal and git-ignored.
