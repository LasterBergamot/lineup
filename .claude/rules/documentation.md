---
paths:
  - "documentation/**"
  - "README.md"
  - "scripts/docs_references.py"
  - ".github/workflows/wiki-sync.yml"
---

# Writing documentation

- After any change that affects current-state or roadmap facts (architecture, API surface, data model, dev workflow, planned work): update the relevant file(s) under `documentation/` to match — it's mirrored into the GitHub wiki by CI, so it needs to stay current the same way `README.md` does.
- `documentation/Newcomer-Guide.md` (wiki: *Newcomer Guide*) is the junior-developer walkthrough: tools and why we use them, glossary, one request through the layers, how to run, test and make a first change. Keep it current when the architecture, the request flow, the tooling or the contribution workflow changes.
- `documentation/References.md` (wiki: *References*) lists the official docs for every library, tool, service, spec and regulation we use. Its *Libraries, images and actions* block is generated: after changing a dependency, `Dockerfile` or workflow run `task docs:references` (CI's `task docs:check` fails on a stale block). Add a row to the handwritten tables when you adopt a new service, tool, spec or regulation.
- Every new file in `documentation/` must also be added to `PAGE_MAP` in `.github/workflows/wiki-sync.yml` (a test and the workflow fail otherwise) and linked from `documentation/Home.md`.
- Write `README.md` and `documentation/` so a newcomer with no prior context can understand the architecture, the codebase, and how a request flows through it — explain the "why", not just record what changed. Keep that bar on every doc update.
