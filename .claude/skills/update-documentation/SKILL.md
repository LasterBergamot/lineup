---
name: update-documentation
description: Update the documentation/ folder (the GitHub wiki mirror) to reflect recent changes to the app's architecture, API surface, data model, dev workflow, or planned work. Use after making a change that affects any of those, or when asked to sync/update the wiki content.
---

`documentation/` is the source of truth for the project's GitHub wiki. It's mirrored 1:1 into
the wiki by `.github/workflows/wiki-sync.yml` on every push to `main` that touches
`documentation/**` — so keeping it current is what keeps the wiki current. This mirrors the
existing `CLAUDE.md`/`README.md` update habit, just for wiki-facing content instead of
dev-facing content.

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
2. For each fact category affected, update the matching file:
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
