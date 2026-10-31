---
name: triage-dependabot
description: Check open Dependabot security alerts and version-update PRs, classify each PR as blocking or non-blocking per the project's `.claude/context/pr-checklist.md`, and (after the user confirms) rebase/merge the safe ones and bring the current branch up to date. Use before opening any PR (create-pr runs it), or when asked about dependency updates, Dependabot, or security alerts.
model: sonnet
---

This puts the Dependabot rule of **`.claude/context/pr-checklist.md`** into practice. Read
that file first: it names the repo (`$REPO`), the base branch, the core dependencies, the
required checks, the lock-file and re-test commands, and any known recurring cases. If the
file and this skill disagree, the file wins.

Everything up to step 4 is read-only. Rebasing, merging and commenting are state-changing:
list what you intend to do and get an explicit go-ahead first.

## 1. Security alerts

```bash
gh api repos/$REPO/dependabot/alerts \
  --jq '[.[] | select(.state=="open") | {number, severity: .security_advisory.severity, package: .dependency.package.name, summary: .security_advisory.summary}]'
```

Report every open alert with its severity. Alerts are separate from version-update PRs: an
empty list here says nothing about pending PRs.

## 2. Version-update PRs

```bash
gh pr list --repo $REPO --state open --author "app/dependabot" \
  --json number,title,mergeable,headRefName,updatedAt
gh pr checks <n> --repo $REPO
gh pr view <n> --repo $REPO --json body,files
```

## 3. Classify each PR

A PR is **blocking** if any of these hold:

- **CI fails.** Read the failing log (`gh run view <run-id> --log-failed`) before judging. If
  the failure is environmental and already fixed on the base branch, it isn't the PR's fault:
  propose `@dependabot rebase` and re-check.
- **It has merge conflicts** (`mergeable` is `CONFLICTING`).
- **It's a major-version bump, or touches a core dependency** (the list is in the checklist),
  and you can't show it's safe for this branch's code.

  To show it is safe, read the upstream release notes for **every** major version in between:

  ```bash
  gh api repos/<owner>/<repo>/releases --jq '.[] | select(.tag_name|test("^v?N\\.0\\.0$")) | .body'
  ```

  Grep this repo for each breaking change. Code paths that the PR's CI doesn't exercise count
  as unverified: say so explicitly.

Otherwise it's **non-blocking**. Check the checklist's known recurring cases (for example a
linter bump that adds new rule violations) before deciding.

## 4. Report

| PR | Bump | CI | Verdict | Reason / evidence |
|---|---|---|---|---|

Also list the open alerts. For each blocking PR, propose a next step: rebase, a new issue (use
the `new-issue` skill), or waiting for an upstream fix.

## 5. Act (only after the user confirms)

- **Rebase a stale PR:** `gh pr comment <n> --repo $REPO --body "@dependabot rebase"`, then
  re-check its CI with `gh pr checks <n> --repo $REPO --watch`.
- **Merge the non-blocking PRs** with the merge method the checklist names, for example
  `gh pr merge <n> --repo $REPO --merge`.
- **Then update the current branch:** `git fetch origin && git merge origin/<base>`. Resolve
  lock-file conflicts by keeping both sides' intent and regenerating the lock with the
  command the checklist names, never by hand-editing it. Then run the checklist's re-test
  commands.
- **For a blocking PR that has a tracking issue**, comment on it with a link to that issue.
