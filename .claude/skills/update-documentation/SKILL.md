---
name: update-documentation
description: Update documentation/ (the GitHub wiki mirror), README.md, CLAUDE.md, and any other project docs that are out of sync with the current state of the project. Use after making a change that affects architecture, API surface, data model, dev workflow, or planned work — or whenever asked to sync/update docs or the wiki content.
---

Keep every doc in the repo honest, not just `documentation/`. `documentation/` is the source
of truth for the project's GitHub wiki — it's mirrored 1:1 into the wiki by
`.github/workflows/wiki-sync.yml` on every push to `main` that touches `documentation/**` —
but `README.md`, `CLAUDE.md`, and any other doc file (e.g. `in-memory-db-plan.md`) can drift
out of sync with the code just as easily, and should be checked and updated in the same pass
rather than treated as someone else's job.

## Files and their scope

| File | Covers |
|------|--------|
| `Home.md` | Wiki landing page — links to the other 6 pages |
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

1. Identify what changed — read the actual diff or current code state (`lineup/`, `app.py`,
   `Taskfile.yml`, `Dockerfile`, `compose.yml`, `in-memory-db-plan.md`) rather than relying on
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
6. Do not touch the wiki directly — edits here get pushed to `main` and synced by CI; direct
   wiki edits get silently overwritten by the next sync.
7. Check `README.md` for the same change: API behavior, prerequisites, available tasks,
   project structure tree, or examples that no longer match reality. Update it directly (not
   via the wiki-sync path — `README.md` isn't mirrored anywhere).
8. Check `CLAUDE.md` too: module list, API shape, container setup, tasks, conventions, or
   project structure that changed. Update it directly.
9. Check any other standalone doc referenced by the change (e.g. `in-memory-db-plan.md`) and
   update it if it's now stale, rather than assuming it's someone else's responsibility.
