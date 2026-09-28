# Lineup — Wiki Home

**Lineup** is a water polo lineup document generator. It takes match details and player
info, fills a `.docx` template (`resources/rajtlista.docx`), and returns the result via a
REST API as either a PDF (default, via LibreOffice headless conversion) or a DOCX. It also
has a persistence layer (Teams, Players, Saved Lineups) so a lineup can be built from a
saved roster instead of a one-off request payload.

- Source repo: [LasterBergamot/lineup](https://github.com/LasterBergamot/lineup)
- Day-to-day project context lives in the repo's `CLAUDE.md` (architecture, conventions,
  dev workflow) and `README.md` (API usage, prerequisites). This wiki is for the
  higher-level narrative and diagrams that don't belong in either of those.

## Current State

- [[Current State: Backend]] — API surface, module architecture, data model, PDF pipeline
- [[Current State: Frontend]] — not started yet
- [[Current State: Everything Else]] — dev workflow, containerization, testing philosophy

## Roadmap

- [[Roadmap: Backend]] — Supabase/Postgres cutover, RLS, team collaboration & invitations
- [[Roadmap: Frontend]] — planned OAuth flow, onboarding, team management UI
- [[Roadmap: Everything Else]] — cross-cutting rollout concerns not specific to one side
