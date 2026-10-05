---
name: update-documentation
description: Update documentation/ (the GitHub wiki mirror), README.md, CLAUDE.md, and any other project docs that are out of sync with the current state of the project. Use after making a change that affects architecture, API surface, data model, dev workflow, or planned work — or whenever asked to sync/update docs or the wiki content.
---

Keep every doc in the repo honest, not just `documentation/`. `documentation/` is the source
of truth for the project's GitHub wiki — it's mirrored 1:1 into the wiki by
`.github/workflows/wiki-sync.yml` on every push to `develop` that touches `documentation/**` —
but `README.md`, `CLAUDE.md`, and any other doc file (e.g. `backend/.env.example`) can drift
out of sync with the code just as easily, and should be checked and updated in the same pass
rather than treated as someone else's job.

Write for a newcomer: every doc should let someone with no prior context on this repo understand
the architecture and codebase, not just record what changed. Explain the "why", not only the "what".

## Files and their scope

| File | Covers |
|------|--------|
| `Home.md` | Wiki landing page — links to every other page |
| `Newcomer-Guide.md` | Junior-developer walkthrough: tools and why, glossary, one request through the layers, run/test, first change, gotchas |
| `References.md` | Official docs for every library, tool, service, spec and regulation; the *Libraries, images and actions* block is generated |
| `Current-State-Backend.md` | Backend architecture, API surface, data model as they exist *today* |
| `Current-State-Frontend.md` | Frontend as it exists today (currently: none exists) |
| `Current-State-Everything-Else.md` | Cross-cutting current state — container/deploy, dev workflow, conventions |
| `Roadmap-Backend.md` | Planned backend work (e.g. auth, `team_members`/`team_invitations`) |
| `Roadmap-Frontend.md` | Planned frontend work |
| `Roadmap-Everything-Else.md` | Cross-cutting planned work |

Cross-links between pages use `[[Page Name]]` wiki-link syntax with the page's *display
title* (e.g. `[[Current State: Backend]]`), not the filename — GitHub preserves colons in
wiki filenames (only spaces become hyphens), and the sync workflow's rename map already
accounts for this, so link text should match the title format already used across these
files, not `documentation/`'s filesystem-safe filenames.

## Steps

1. Identify what changed — read the actual diff or current code state (`backend/lineup/`, `backend/app.py`,
   `Taskfile.yml`, `backend/Dockerfile`, `compose.yml`, `backend/.env.example`). The Python
   code lives in `backend/`, and every Python command runs with that as its working directory. rather than relying on
   memory of what the docs currently say.
2. For each fact category affected, update the matching `documentation/` file:
   - Architecture / API surface / data model change → `Current-State-Backend.md` (or
     `-Frontend.md` if a frontend exists by then)
   - Dev workflow, container, or conventions change → `Current-State-Everything-Else.md`
   - A plan changed, was completed (move it out of Roadmap into Current-State), or a new
     future item was scoped → the matching `Roadmap-*.md`
3. Keep Mermaid diagrams in sync with prose — if a sequence/flow changed, update the diagram,
   don't just leave stale prose next to it.
4. If a roadmap item was completed, move its content from the `Roadmap-*` page to the
   matching `Current-State-*` page rather than leaving it duplicated in both.
5. If `Home.md`'s summary of a page's contents no longer matches (e.g. a page's scope shifted
   materially), update `Home.md` too.
6. Do not touch the wiki directly — edits here get merged into `develop` and synced by CI; direct
   wiki edits get silently overwritten by the next sync.
7. Check `README.md` for the same change: API behavior, prerequisites, available tasks,
   project structure tree, or examples that no longer match reality. Update it directly (not
   via the wiki-sync path — `README.md` isn't mirrored anywhere).
8. Check `CLAUDE.md` too: module list, API shape, container setup, tasks, conventions, or
   project structure that changed. Update it directly.
9. Check any other standalone doc referenced by the change (e.g. `backend/.env.example`) and
   update it if it's now stale, rather than assuming it's someone else's responsibility.
10. Newcomer Guide: if the change alters the architecture, request flow, tooling, commands or
    the contribution workflow, update `Newcomer-Guide.md` (keep it written for a junior
    developer: explain the "why", define jargon in the glossary).
11. References: run `task docs:references` whenever a dependency, `Dockerfile` or workflow
    changed, and add a row to the handwritten tables of `References.md` for any new service,
    tool, spec or regulation. `task docs:check` must pass.
12. A new file in `documentation/` must be added to `PAGE_MAP` in `.github/workflows/wiki-sync.yml`
    and linked from `Home.md`.
13. Docstrings: for every public module, class, function or method the change added or altered
    in `backend/lineup/`, `app.py` or `main.py`, check that the docstring is present (ruff `D1`
    enforces that) **and still true**. It should say what the thing is for, the non-obvious why
    and what it raises or returns, for a junior reader. Pydantic models and route functions
    show up in `/docs`, so phrase those for an API consumer.
14. If nothing needs documenting, say so explicitly (`No doc impact: <reason>`); the PR must
    carry that line and the `no-docs` label.
