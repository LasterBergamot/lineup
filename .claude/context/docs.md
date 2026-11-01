# Doc map

Read by the `update-documentation` skill (from `ai-common`). The skill holds the procedure;
this file says which docs this repo has and the steps that are specific to it.

## Where the docs are

- `documentation/` is the source of the project's GitHub wiki. `.github/workflows/wiki-sync.yml`
  mirrors it 1:1 on every push to `develop` that touches `documentation/**`. Never edit the
  wiki directly: the next sync overwrites it.
- `README.md` (not mirrored anywhere): API behavior, prerequisites, tasks, the **only** copy of
  the project structure tree.
- `CLAUDE.md` is a router (keep it under 100 lines; a test enforces it). The detail lives in
  `.claude/rules/` (one file per area, loaded by path) and `.claude/context/`.
  `.claude/context/claude-code.md` maps "what you changed" to "which file to update".
- Other standalone docs, e.g. `backend/.env.example`, `PLAN.md`.

## `documentation/` pages

| File | Covers |
|------|--------|
| `Home.md` | Wiki landing page; links to every other page |
| `Setup.md` | From a fresh clone to a working dev environment, step by step (people and agents) |
| `Newcomer-Guide.md` | Junior-developer walkthrough: tools and why, glossary, one request through the layers, run/test, first change, gotchas |
| `References.md` | Official docs for every library, tool, service, spec and regulation; the *Libraries, images and actions* block is generated |
| `Auth-Setup.md`, `Fly-Setup.md`, `Pages-Setup.md` | Runbooks for sign-in, the API host and the web-app host |
| `Supabase-Admin-Guide.md` | Operator guide to fixing or deleting dev data by hand in Supabase Studio (cascades, backup first, what not to do). Update it when a foreign key's `ondelete` rule or a table changes |
| `Privacy-and-Security.md` | GDPR source of truth: roles, the personal-data inventory (every model column), retention, sub-processors and regions, backups, open gaps. A new column, endpoint that stores people data, processor or browser-storage key needs a row here in the same PR |
| `Privacy-Notice.md`, `Terms-and-Processor-Agreement.md`, `Compliance-Records.md`, `Breach-Runbook.md` | Built from the page above: HU + EN notices and the club Art. 14 template, ToS + Art. 28 agreement, Art. 30 records + LIA + DPIA screening, breach runbook. Change them in the same PR when a fact on `Privacy-and-Security.md` changes. `[…]` placeholders are the operator's to fill in |
| `Current-State-Backend.md` | Backend architecture, API surface, data model as they exist today |
| `Current-State-Frontend.md` | The frontend as it exists today |
| `Current-State-Everything-Else.md` | Cross-cutting current state: container/deploy, dev workflow, conventions, CI |
| `Roadmap-Backend.md`, `Roadmap-Frontend.md`, `Roadmap-Everything-Else.md` | Planned work per area |

Cross-links between pages use `[[Page Name]]` with the page's *display title* (e.g.
`[[Current State: Backend]]`), not the filename: GitHub keeps colons in wiki filenames (only
spaces become hyphens), and the sync workflow's rename map accounts for this.

## Steps specific to this repo

- Architecture / API / data model → `Current-State-Backend.md` (or `-Frontend.md`). Dev
  workflow, container, conventions → `Current-State-Everything-Else.md`. Plans →
  `Roadmap-*.md`; when one is done, move it to the matching `Current-State-*` page.
- A new file in `documentation/` must be added to `PAGE_MAP` in
  `.github/workflows/wiki-sync.yml` (a test and the workflow fail otherwise) and linked from
  `Home.md`.
- Newcomer Guide: update it when the architecture, request flow, tooling, commands or the
  contribution workflow change. Keep it written for a junior developer.
- References: run `task docs:references` whenever a dependency, `Dockerfile` or workflow
  changed (`task docs:check` must pass), and add a row to the handwritten tables for any new
  service, tool, spec or regulation.
- Docstrings: every public module, class, function or method the change added or altered in
  `backend/lineup/`, `app.py` or `main.py` needs a docstring (ruff `D1` checks presence) that
  is **still true**: what it is for, the non-obvious why, what it raises or returns. Pydantic
  models and route functions show up in `/docs`, so phrase those for an API consumer.
- The Python code lives in `backend/`, and every Python command runs with that as its
  working directory.
- No doc change: the PR carries `No doc impact: <reason>` and the `no-docs` label.
