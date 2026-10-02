---
name: repo-audit
description: Audit the whole lineup repo for bugs, contradicting logic, design flaws, security issues, doc drift and flawed plans, then reconcile the findings with the GitHub issues and project board. Use when asked to audit, review or health-check the repository (not a single diff — use code-review for that), or periodically before planning a new milestone.
model: opus
effort: high
---

Audit the repository end to end, verify the serious findings yourself, and turn them into
GitHub issue changes the user approves. This is the process that produced epics #40–#46 in
Oct 2026; rerun it the same way so results stay comparable.

**Read-only until the user approves.** Steps 1–4 change nothing. Every git/`gh` write in
step 5 needs the user's explicit go-ahead, stage by stage (see the user's global CLAUDE.md:
approving a plan is not approval for a batch of writes).

## 1. Context

1. Read `CLAUDE.md`, and skim `README.md` and `documentation/Roadmap-*.md`.
2. `git log --oneline -40` and `git status`, to know what changed since the last audit.
   Search the issues for "Found in the Oct 2026 repository audit" to see what is already tracked.

## 2. Fan out: three parallel Explore agents

Launch all three in **one message** so they run concurrently. Each is read-only and must
report findings as `file:line`, a short quote, an explanation and a severity (high/med/low),
verified against the code rather than guessed.

- **Code.** Read in full: `app.py`, `main.py`, `lineup/**`, `alembic/env.py`,
  `alembic/versions/*`, `tests/**`, `pyproject.toml`. Hunt for:
  - validation mismatches between `lineup/api/models.py` and the saved-lineup schemas;
  - ORM vs migration drift (nullable, ondelete, indexes, server defaults, constraints);
  - async SQLAlchemy pitfalls (identity map, selectin, rollbacks);
  - blocking calls inside `async def`; LibreOffice timeouts, concurrency and error mapping;
  - owner/user filtering consistency, and fail-open behaviour when the id is `None`;
  - header and filename injection; input limits; layering violations; dead code;
  - tests that assert the wrong thing; the coverage config.
- **Docs, infra and CI.** Read: `CLAUDE.md`, `README.md`, `documentation/*`, `Taskfile.yml`,
  `Dockerfile`, `compose.yml`, `.dockerignore`, `.env.example`, `.gitignore`, `.github/**`,
  `.claude/**`. Hunt for:
  - docs that contradict each other or the code (verify structure trees with `ls`/`find`;
    task names vs the Taskfile; endpoints vs `lineup/*/router.py`);
  - roadmap items already done, or technically unworkable (e.g. RLS while the app connects
    as a role that bypasses RLS);
  - Docker: root user, healthcheck, pinning, what `COPY . .` pulls in;
  - CI: `permissions`, `concurrency`, SHA pinning, `--locked`, caching, whether migrations run;
  - Dependabot ecosystems and groups; stale skill or command instructions.
- **GitHub state** (read-only `gh` only). Collect:
  - all issues with body, labels, milestone and assignee;
  - parent/sub-issue and `blockedBy`/`blocking` relations via GraphQL;
  - project #4 items and their Status/Area/Priority/Size fields;
  - labels, milestones, PRs with `closingIssuesReferences`;
  - open Dependabot PRs and their checks;
  - open Dependabot alerts (`gh api repos/LasterBergamot/lineup/dependabot/alerts`);
  - branch protection and repo settings.

  Cross-reference with the roadmap docs and `git log`, and report:
  - open issues that are already done, and closed issues that aren't;
  - duplicates;
  - issues missing labels, milestone, board entry or acceptance criteria;
  - stale `#N` references, and relationships that point at closed issues;
  - roadmap items with no issue.

## 3. Verify before you trust

Subagent findings are leads, not facts. For every **high/P0–P1** finding, read the cited
lines yourself, and reproduce it where that's cheap (e.g. a tiny ASGI request against
in-memory SQLite, or `docker run --rm lineup ls -a /app`). Drop or downgrade anything that
doesn't hold up. Mark what you reproduced as **[verified]**.

## 4. Report and plan (still read-only)

Write the plan file with:

1. **Findings**: a P0 table (`# | finding | location`), then P1/P2 grouped by theme
   (authorization, API correctness, data layer, PDF, design, tests, Docker/Compose, CI,
   Taskfile, docs drift, `.claude` tooling).
2. **Hotfix scope**: only the P0s that are low-risk to fix now, on one branch.
3. **GitHub changes**, as a reviewable draft:
   - repo settings; labels (`type:*`, `area:*`, `priority:*`); milestones;
   - board fields; edits to existing issues; new epics with sub-issues;
   - relationships, i.e. parent and blocked-by links.
   Write every new issue body as **Problem / Evidence (file:line) / Proposal / Acceptance**
   and end it with an audit marker line.
4. **Verification** steps.

Ask the user at most a few `AskUserQuestion`s that change the outcome. Typical ones: whether
to hotfix or only file issues, whether to keep one board or several, and how big issues
should be.

## 5. Apply (after approval)

- **Hotfix:** follow `CLAUDE.md`. Write tests (coverage stays at 100 %), run `task lint`,
  `task test` and `task test-e2e` if the PDF/container path changed, then run the
  `update-documentation` skill. Branch, commit and PR each need explicit approval; use the
  `create-pr` skill for the PR.
- **GitHub:** put the data (labels, issues, edits, relations) in a scratch file outside the
  repo, e.g. `/tmp/<audit>/data.py`. Apply it in stages, showing the exact commands and
  asking before each one:

  1. repo settings
  2. labels
  3. milestones
  4. create issues
  5. resolve placeholder refs and edit existing issues
  6. relationships
  7. board
  8. closures
  9. Dependabot comments

  Use the `new-issue` skill's recipes for labels, board fields, sub-issues and blocked-by.
  Keep the created numbers in a state file so a failed stage can be resumed safely.
- Finish with a read-only check: no open issue without labels or a milestone, the
  relationships as planned, all open issues on the board.
