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
- Day-to-day project context for AI assistants lives in the repo: `CLAUDE.md` is a short router
  that points at `.claude/rules/` (conventions per area, loaded when you touch that area) and
  `.claude/context/` (workflow, PR checklist). This wiki is for the higher-level narrative and diagrams that don't belong
  in either of those.

## Guides and references

- [[Newcomer Guide]] — the junior-developer walkthrough: stack, glossary, request flow, running,
  testing, your first change, common gotchas
- [[Setup]] — from a fresh clone to a working dev environment, step by step, with the expected
  result of each step (for people and AI agents alike); starts with `task doctor`
- [[Auth Setup]] — how Google sign-in through Supabase works, the one-off dashboard setup, adding
  and removing testers, and what each `401`/`503` means
- [[Fly Setup]] — how the API runs on Fly.io (scale to zero, EU region), creating the dev app,
  secrets, deploying and troubleshooting
- [[Pages Setup]] — how the web app is hosted on Cloudflare Pages, creating the dev site, build
  variables, the allow-lists to update, and why PR previews cannot sign in
- [[Supabase Admin Guide]] — fixing or removing dev data by hand in Supabase Studio: finding a user or
  team, what each delete cascades to, revoking an invitation, backing up first and what never to do
- [[Privacy and Security]] — who is controller and processor, the personal-data inventory (field →
  table → purpose → basis → retention), sub-processors and regions, backups, what is not built yet
  and the checklist before inviting anyone. The next four pages are built from it:
  [[Privacy Notice]] (Hungarian + English, with the Art. 14 template for clubs),
  [[Terms and Processor Agreement]], [[Compliance Records]] (Art. 30, legitimate-interest
  assessment, DPIA screening) and [[Breach Runbook]]
- [[References]] — official docs and links for every library, tool, service, spec and regulation
  we use (the dependency tables are generated from the repo)

## Current State

- [[Current State: Backend]] — API surface, module architecture and request flow, data model,
  database configuration (SQLite vs. Supabase), Alembic workflow, credential recovery,
  portability to other stacks, PDF pipeline
- [[Current State: Frontend]] — React + Vite skeleton: theme, app shell, generated API client
- [[Current State: Everything Else]] — environment variables, dev workflow, containerization,
  testing philosophy, CI and security tooling

## Roadmap

- [[Roadmap: Backend]] — production Supabase project, team-scoped RLS (auth, team collaboration and
  invitations are done; so is the dev-database cutover)
- [[Roadmap: Frontend]] — planned OAuth flow, onboarding, team management UI
- [[Roadmap: Everything Else]] — branching model and environments (dev/test), cross-cutting
  rollout concerns not specific to one side
