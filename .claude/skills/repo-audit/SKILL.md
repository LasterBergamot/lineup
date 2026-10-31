---
name: repo-audit
description: Audit the whole repository for bugs, contradicting logic, design flaws, security issues, doc drift and flawed plans, then reconcile the findings with the GitHub issues and project board. Use when asked to audit, review or health-check the repository (not a single diff — use code-review for that), or periodically before planning a new milestone.
model: opus
effort: high
---

Audit the repository end to end, verify the serious findings yourself, and turn them into
GitHub issue changes the user approves. The project's audit setup lives in
**`.claude/context/audit.md`**: what each explorer reads and hunts for, the repo and board,
the marker line earlier audits used, and which checks belong to other skills (for example a
compliance audit). Read it first, so each audit is comparable with the last one.

**Read-only until the user approves.** Steps 1–4 change nothing. Every git/`gh` write in
step 5 needs the user's explicit go-ahead, stage by stage. Approving a plan is not approval
for a batch of writes.

## 1. Context

1. Read `CLAUDE.md` (or `AGENTS.md`), the rule and context files it routes to, the README and
   the roadmap docs.
2. `git log --oneline -40` and `git status`, to know what changed since the last audit.
   Search the issues for the previous audit's marker line to see what is already tracked.

## 2. Fan out: three parallel explorers

Launch all three in **one message** so they run concurrently. Each is read-only and reports
findings as `file:line`, a short quote, an explanation and a severity (high/med/low),
verified against the code rather than guessed. Put the scope and hunt list from the audit
context file into each prompt (explorer agents don't load `CLAUDE.md`).

- **Code**: the source, migrations, tests and build config.
- **Docs, infra and CI**: the docs, task runner, containers, CI workflows, dependency bots and
  the assistant setup (stale skill or command instructions included).
- **GitHub state** (read-only `gh` only): issues with labels and milestones, parent/sub-issue
  and blocked-by relations, board fields, PRs with their closing references, Dependabot PRs
  and alerts, branch protection. Report done-but-open and open-but-done issues, duplicates,
  missing metadata, stale `#N` references and roadmap items with no issue.

## 3. Verify before you trust

Explorer findings are leads, not facts. For every high or P0–P1 finding, read the cited lines
yourself and reproduce it where that's cheap. Drop or downgrade anything that doesn't hold up.
Mark what you reproduced as **[verified]**.

## 4. Report and plan (still read-only)

Write a plan file with:

1. **Findings:** a P0 table (`# | finding | location`), then P1/P2 grouped by theme.
2. **Hotfix scope:** only the P0s that are low-risk to fix now, on one branch.
3. **GitHub changes**, as a reviewable draft: settings, labels, milestones, board fields,
   edits to existing issues, new epics with sub-issues, relationships. Write every new issue
   body as Problem / Evidence (file:line) / Proposal / Acceptance and end it with the
   project's audit marker line.
4. **Verification** steps.

Ask the user only the few questions that change the outcome.

## 5. Apply (after approval)

- **Hotfix:** follow the project's branch rules, write tests, run the gates from
  `.claude/context/pr-checklist.md`, run `update-documentation`, and open the PR with
  `create-pr`. Branch, commit and PR each need explicit approval.
- **GitHub:** keep the data in a scratch file outside the repo, and apply it in stages
  (settings, labels, milestones, new issues, edits, relationships, board, closures), showing
  the commands and asking before each. Use the `new-issue` skill's recipes. Keep the created
  numbers in a state file so a failed stage can be resumed.
- Finish with a read-only check: no open issue without labels or a milestone, relationships
  as planned, all open issues on the board.
