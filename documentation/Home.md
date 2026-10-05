# Lineup — Wiki Home

**Lineup** is a water polo lineup document generator. It takes match details and player
info, fills a `.docx` template (`backend/resources/rajtlista.docx`), and returns the result via a
REST API as either a PDF (default, via LibreOffice headless conversion) or a DOCX. It also
has a persistence layer (Teams, Players, Saved Lineups) so a lineup can be built from a
saved roster instead of a one-off request payload.

- Source repo: [LasterBergamot/lineup](https://github.com/LasterBergamot/lineup)
- New here? Read the [[Newcomer Guide]] (what each tool is and why we use it, a glossary, one
  request walked through the code, how to make a first change). The repo's `README.md` covers
  setup and running; then read [[Current State: Backend]].
- Day-to-day project context lives in the repo's `CLAUDE.md` (architecture, conventions,
  dev workflow). This wiki is for the higher-level narrative and diagrams that don't belong
  in either of those.

## Guides and references

- [[Newcomer Guide]] — the junior-developer walkthrough: stack, glossary, request flow, running,
  testing, your first change, common gotchas
- [[Auth Setup]] — how Google sign-in through Supabase works, the one-off dashboard setup, adding
  and removing testers, and what each `401`/`503` means
- [[References]] — official docs and links for every library, tool, service, spec and regulation
  we use (the dependency tables are generated from the repo)

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
- [[Roadmap: Everything Else]] — branching model and environments (dev + prod), cross-cutting
  rollout concerns not specific to one side
