# Lineup — Wiki Home

**Lineup** is a water polo lineup document generator. It takes match details and player
info, fills a `.docx` template (`resources/rajtlista.docx`), and returns the result via a
REST API as either a PDF (default, via LibreOffice headless conversion) or a DOCX. It also
has a persistence layer (Teams, Players, Saved Lineups) so a lineup can be built from a
saved roster instead of a one-off request payload.

- Source repo: [LasterBergamot/lineup](https://github.com/LasterBergamot/lineup)
- New here? Start with the repo's `README.md` (what the project is, how to set it up and run
  it, how a request is handled), then read [[Current State: Backend]].
- Day-to-day project context lives in the repo's `CLAUDE.md` (architecture, conventions,
  dev workflow). This wiki is for the higher-level narrative and diagrams that don't belong
  in either of those.

## Current State

- [[Current State: Backend]] — API surface, module architecture and request flow, data model,
  database configuration (SQLite vs. Supabase), Alembic workflow, credential recovery,
  portability to other stacks, PDF pipeline
- [[Current State: Frontend]] — not started yet
- [[Current State: Everything Else]] — environment variables, dev workflow, containerization,
  testing philosophy, CI and security tooling

## Roadmap

- [[Roadmap: Backend]] — production Supabase project, auth, RLS, team collaboration &
  invitations (the dev-database cutover is already done)
- [[Roadmap: Frontend]] — planned OAuth flow, onboarding, team management UI
- [[Roadmap: Everything Else]] — cross-cutting rollout concerns not specific to one side
