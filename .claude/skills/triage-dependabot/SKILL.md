---
name: triage-dependabot
description: Check open Dependabot security alerts and version-update PRs for LasterBergamot/lineup, classify each PR as blocking or non-blocking per CLAUDE.md, and (after the user confirms) rebase/merge the safe ones and bring the current branch up to date. Use before opening any PR (create-pr runs it), or when asked about dependency updates, Dependabot, or security alerts.
model: sonnet
---

This puts into practice the Dependabot rule in `CLAUDE.md` ("Before creating a PR …"). Read
that section first; if it and this skill disagree, CLAUDE.md wins and this file is stale.

Everything up to step 4 is read-only. Rebasing, merging and commenting are state-changing:
list what you intend to do and get an explicit go-ahead first.

## 1. Security alerts

```bash
gh api repos/LasterBergamot/lineup/dependabot/alerts \
  --jq '[.[] | select(.state=="open") | {number, severity: .security_advisory.severity, package: .dependency.package.name, summary: .security_advisory.summary}]'
```

Report every open alert with its severity. Alerts are separate from version-update PRs: an
empty list here says nothing about pending PRs.

## 2. Version-update PRs

```bash
gh pr list --repo LasterBergamot/lineup --state open --author "app/dependabot" \
  --json number,title,mergeable,headRefName,updatedAt
gh pr checks <n> --repo LasterBergamot/lineup
gh pr view <n> --repo LasterBergamot/lineup --json body,files
```

## 3. Classify each PR

A PR is **blocking** if any of these hold:

- **CI fails.** Read the failing log (`gh run view <run-id> --log-failed`) before judging.
  If the failure is environmental and already fixed on `main` (e.g. the `setup-task` API
  rate limit, fixed by passing `repo-token` to `arduino/setup-task`), it isn't the PR's fault: propose `@dependabot rebase`
  and re-check.
- **It has merge conflicts** (`mergeable` is `CONFLICTING`).
- **It's a major-version bump, or touches a core dependency** (SQLAlchemy, FastAPI, asyncpg,
  pydantic, alembic, python-docx), and you can't show it's safe for this branch's code.

  To show it is safe, read the upstream release notes for **every** major version in
  between:

  ```bash
  gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name|test("^v?N\\.0\\.0$")) | .body'
  ```

  Grep this repo for each breaking change, e.g. "credentials persisted to a separate file"
  → does any workflow `git push` after checkout? Paths that the PR's CI doesn't exercise
  (e.g. `wiki-sync.yml` only runs on `main`) count as unverified: say so explicitly.

Otherwise it's **non-blocking**.

Known recurring case: a linter major/minor bump (ruff) that adds new rule violations is
blocking until a dedicated issue fixes them. #62 tracks ruff 0.16 / PR #27.

## 4. Report

| PR | Bump | CI | Verdict | Reason / evidence |
|---|---|---|---|---|

Also list the open alerts. For each blocking PR, propose a next step: rebase, a new issue
(use the `new-issue` skill), or waiting for an upstream fix.

## 5. Act (only after the user confirms)

- **Rebase a stale PR:**

  ```bash
  gh pr comment <n> --repo LasterBergamot/lineup --body "@dependabot rebase"
  ```

  Then re-check its CI (`gh pr checks <n> --watch`).
- **Merge the non-blocking PRs:**

  ```bash
  gh pr merge <n> --repo LasterBergamot/lineup --squash
  ```

  Branch protection requires `Lint & test` and `E2E (real PDF conversion)` to be green.
- **Then update the current branch:**

  ```bash
  git fetch origin && git merge origin/main
  ```

  Resolve `pyproject.toml`/`uv.lock` conflicts by keeping both sides' intent, then
  regenerate the lock with `uv lock` rather than hand-editing it. Then:

  ```bash
  uv sync
  task lint
  task test
  ```

- **For a blocking PR that has a tracking issue**, comment on it with a link to that issue.
