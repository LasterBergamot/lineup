---
name: update-documentation
description: Update the project's docs (README, the wiki or docs folder, CLAUDE.md and its rule/context files, docstrings and any other doc file) that are out of sync with the current state of the project. Use after making a change that affects architecture, API surface, data model, dev workflow, or planned work — or whenever asked to sync/update docs or the wiki content.
model: sonnet
---

Keep every doc in the repo honest, not just one folder. The project's doc map lives in
**`.claude/context/docs.md`**: which files exist, what each one covers, how they are
published (for example a wiki mirror), and the project-specific steps (generated blocks,
page maps, docstring rules). Read it first; this skill holds the procedure.

Write for a newcomer: every doc should let someone with no prior context understand the
architecture and codebase, not just record what changed. Explain the "why", not only the "what".

## Steps

1. **Identify what changed.** Read the actual diff or the current code, not your memory of
   what the docs say.
2. **Update the matching pages** from the doc map: current-state pages for what exists today,
   roadmap pages for what is planned. When a planned item is done, move it from the roadmap
   page to the current-state page instead of leaving it in both.
3. **Keep diagrams in sync with prose.** If a flow changed, update the diagram too.
4. **Keep the index current.** If a page's scope shifted, update the landing page's summary.
   A new page goes into the index (and the page map, if the project publishes one).
5. **Don't edit published copies directly** (for example a GitHub wiki that CI overwrites).
6. **README:** API behavior, prerequisites, tasks, project structure and examples must match.
7. **Assistant context:** `CLAUDE.md` (or `AGENTS.md`) and the rule and context files it
   routes to. Keep the router short; the detail lives in the rule files.
8. **Other docs the change touches** (env examples, runbooks, setup guides).
9. **The newcomer guide and the references page**, if the project has them and the change
   affects tooling, architecture or dependencies.
10. **Project-specific steps** from the doc map (generated blocks, docstring rules, page maps).
11. **If nothing needs documenting, say so explicitly**, in the form the project's PR rules
    ask for (see `.claude/context/pr-checklist.md`).
