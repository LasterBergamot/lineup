---
name: create-pr
description: Prepare and open a pull request for the current branch — Dependabot triage, the project's quality gates, docs sync, then a PR with a structured body and Closes/Refs links. Use when the user asks to open, create or raise a PR, or says a branch is ready for review.
model: sonnet
---

The project's rules for PRs live in **`.claude/context/pr-checklist.md`**: the repo
(`$REPO`), the base branch, the protected branches and required checks, the gates (lint, tests,
end-to-end tests and when they apply, compliance checks), the docs check, and the merge method.
Read it first. This skill holds the procedure; the checklist holds the values. If they
disagree, the checklist wins.

Committing, pushing, merging Dependabot PRs and creating the PR are all state-changing git or
`gh` commands. Show what you're about to do and get an explicit go-ahead for each, unless the
user has already approved that step in this session. Approving the PR doesn't approve
unrelated merges.

## 1. Know what's in the branch

```bash
git status --short
git log --oneline origin/<base>..HEAD
git diff --stat origin/<base>...HEAD
```

If you're on a protected branch, stop: propose a branch name first (the checklist gives the
naming scheme). Uncommitted changes need a commit, which needs approval, before anything else.

If the project merges with merge commits, keep the branch history meaningful: every branch
commit lands in the base branch as-is. A follow-up change that belongs to an existing commit
(a typo, a lint fix, a review remark) goes into that commit, not into a new "fix" commit:
`git commit --amend` for the last one, `git commit --fixup=<sha>` plus
`git rebase --autosquash origin/<base>` for an earlier one. Once pushed, rewriting needs
`git push --force-with-lease` (never plain `--force`, never on a protected branch). Ask first.

## 2. Dependabot

Run the `triage-dependabot` skill. Merging any non-blocking PR it finds needs the user's
confirmation. If something was merged, bring this branch up to date as that skill describes.

## 3. Quality gates

Run every gate the checklist lists, in its order: typically a compliance or security quick
check, the linter, the test suite (with its coverage rule), and the end-to-end tests when the
diff touches the paths the checklist names. Tell the user before a gate that stops running
containers or services.

A gate that fails is fixed on the branch, or (only where the checklist allows it) listed in
the PR body with a follow-up issue. Check that every new or changed module has tests.

## 4. Docs

Always run the `update-documentation` skill, whatever the diff, and commit the result after
approval. If the project has a docs-touched check (the checklist names it), run it locally
before opening the PR. A PR without a docs diff needs the opt-out the checklist describes.

## 5. Find the linked issues

```bash
gh issue list --repo $REPO --state open --search "<keywords from the diff>" --json number,title
```

- `Closes #N` only for issues whose **Acceptance** checklist is fully met by this PR.
- `Refs #N` for partial progress. Say in the body which part is done.

## 6. Open the PR

```bash
git push -u origin <branch>
gh pr create --repo $REPO --base <base> --head <branch> --title "<imperative summary>" --body-file - <<'BODY'
## Summary
- **What changed**, and the *why* (the bug or need it addresses)

Closes #N / Refs #M (what part)

## Pre-PR checks
- Dependabot alerts: …
- Dependabot PRs: … (merged / blocking + reason)

## Docs
- Updated: …, or the checklist's no-docs line

## Test plan
- [x] each gate from the checklist, with its result
BODY
```

Use the project's PR template instead if the repo has one (`.github/pull_request_template.md`).
End the body with the attribution line the current session's system reminder specifies, if
there is one.

## 7. Watch CI, then merge only when asked

```bash
gh pr checks <n> --repo $REPO --watch --interval 20
```

Report the PR URL and the check results. If a check fails, read the log
(`gh run view <id> --log-failed`) and propose a fix. Never merge the PR unless the user
explicitly asks. Then use the checklist's merge method, update the base branch locally and
delete the merged branch with `git branch -d <branch>`.
