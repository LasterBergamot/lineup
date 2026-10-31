# Claude Code setup: context layout and skills

## How the project context is organised

`CLAUDE.md` is a router, so a session only carries what it needs:

| Where | Loaded | Holds |
|-------|--------|-------|
| `CLAUDE.md` | at session start | what the project is, the always-on rules, the router table |
| `.claude/rules/*.md` | when Claude reads or edits a file that matches the `paths:` globs in the file's frontmatter | the detail for one area (conventions, gotchas, module tables) |
| `.claude/context/*.md` | only when you (or a skill) read it | workflow, the PR checklist, issue conventions, the doc map, the audit setup, this file |
| `apm.yml`, `apm.lock.yaml` | never by Claude; by the `apm` CLI | which `ai-common` version the generic skills come from (see *Skills* below) |

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
| the PR rules, the Dependabot rule, the gates | `.claude/context/pr-checklist.md` |
| labels, milestones, epics, the board | `.claude/context/issues.md` |
| a docs page added or removed, a docs-specific step | `.claude/context/docs.md` |
| what the repo audit covers | `.claude/context/audit.md` |
| a generic skill (`new-issue`, `create-pr`, `triage-dependabot`, `update-documentation`, `repo-audit`, `setup-project`) or the `convention-reviewer` agent | the `ai-common` repo, not here (see *Skills* below) |
| skills, settings, this layout | this file |
| the project summary, repo layout, always-on rules | `CLAUDE.md` (keep it short) |

The file tree lives only in `README.md` ("Project structure").

## Skills (`.claude/skills/`)

**Two sources.** The project-specific skills live only here: `compliance-audit` (with its
`requirements.md`) and `supabase-smoke`. The generic ones (`new-issue`, `create-pr`,
`triage-dependabot`, `update-documentation`, `repo-audit`, `setup-project`) and the
`convention-reviewer` agent (`.claude/agents/`) come from the owner's private `ai-common` repo,
installed with [APM](https://github.com/microsoft/apm) at the tag pinned in `apm.yml`. They
hold the procedure only; lineup's values (repo, labels, milestones, board, gates, doc map,
audit scope) live in `.claude/context/issues.md`, `pr-checklist.md`, `docs.md` and
`audit.md`, which is where you change them.

- The deployed copies are **committed**, so anyone who clones lineup has the skills without
  access to `ai-common`, and CI needs no token. `apm_modules/` is git-ignored.
- **Never edit a deployed skill here.** `apm audit` reports it as drift and the next install
  overwrites it. Change it in `ai-common`, release a new tag there, then in lineup: change the
  tag in `apm.yml`, run `apm install`, review `git diff .claude/`, and commit `apm.yml`,
  `apm.lock.yaml` and the deployed files together. Run `apm audit` before committing.
- Updating needs the APM CLI and read access to `ai-common` (APM uses your `gh` login).
  Dependabot doesn't track APM dependencies, so the tag is bumped by hand.
- `tests/test_docs_tooling.py` (`TestAiCommonSkills`) fails when a skill names a context file
  that doesn't exist, or when `apm.lock.yaml` lists a deployed file that isn't committed.

**Models: always an alias, never a full ID.** `model:` takes `opus`, `sonnet`, `haiku` or `inherit`. Claude Code resolves an alias to the newest model of that tier (currently Claude 5.5), so the skills move to the next release without anyone editing them; a full ID such as `claude-sonnet-5-5` would go stale. A test (`TestSkillModelAliases`) fails on a full ID or an invalid `effort:` (`low`, `medium`, `high`, `xhigh`, `max`). If a skill seems to run an older model, check your machine, not the repo: the `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL` and `ANTHROPIC_DEFAULT_HAIKU_MODEL` environment variables (set by a launcher or wrapper) override what each alias resolves to; `env | grep ANTHROPIC_DEFAULT` shows them.

From `ai-common`: `repo-audit` (opus): full audit → GitHub reconciliation. Project-only: `compliance-audit` (opus): GDPR/Hungarian/OWASP checks against its `requirements.md`; full audit → compliance matrix → issues, or `quick <issue#|branch>` per feature (run at issue start and as a `create-pr` gate). From `ai-common`: `new-issue` (haiku): labels/milestone/board/relations recipes, values from `issues.md`. `triage-dependabot` (sonnet): the pre-PR Dependabot rule in `pr-checklist.md`. `create-pr` (sonnet): the gates in `pr-checklist.md` + PR. Project-only: `supabase-smoke` (haiku): the live dev-Supabase smoke test (authenticates through `scripts/smoke_auth.py`, a localhost stand-in for Supabase Auth, so no real sign-in is needed; the steps are the committed `scripts/smoke_live.py`, which the `smoke` job in `deploy-dev.yml` also runs after every dev deploy, so change the script, not the skill). From `ai-common`: `update-documentation` (sonnet): sync README, rules, context and the wiki pages, following the doc map in `docs.md`. `setup-project` (haiku, `effort: high`): follows `documentation/Setup.md`, the tool-neutral runbook that people and other agents use too; each step there has an expected result, so a small model that checks every step is enough. Change the steps in that page, not in the skill. The models are pinned with `model:` in each skill's frontmatter and apply only while the skill runs. If you change a workflow these skills encode (labels, milestones, epics, board fields, the Dependabot rule, the gates), update the matching context file in the same change; for the smoke-test steps, update `supabase-smoke`. `.claude/settings.json` (shared) allows `task lint`/`task test` and denies reading `.env*` at the root and `backend/.env*`; `.claude/settings.local.json` is personal and git-ignored.
