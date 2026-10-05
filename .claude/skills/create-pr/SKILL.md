---
name: create-pr
description: Prepare and open a pull request for the current branch of LasterBergamot/lineup — Dependabot triage, lint/test/e2e, docs sync, coverage, then a PR with a structured body and Closes/Refs links. Use when the user asks to open, create or raise a PR, or says a branch is ready for review.
model: sonnet
---

`develop` and `main` are protected: they only change through PRs that pass `Lint & test` and
`E2E (real PDF conversion)` (and, for PRs, `Docs updated`). Feature branches target `develop` (deploys to dev); a release is
a `develop` → `main` PR (deploys to prod). This skill gets a branch into that state and opens the PR.

Committing, pushing, merging Dependabot PRs and creating the PR are all state-changing git
or `gh` commands. Show what you're about to do and get an explicit go-ahead for each.
Approving the PR doesn't approve unrelated merges.

## 1. Know what's in the branch

```bash
git status --short
git log --oneline origin/develop..HEAD
git diff --stat origin/develop...HEAD
```

If you're on `develop` or `main`, stop: propose a branch name first (`fix/…`, `feat/<issue>-…`,
`chore/…`). Uncommitted changes need a commit, which needs approval, before anything else.

Keep the branch's history meaningful, because PRs are merged with a merge commit (step 7),
so every branch commit lands in `develop` as-is. A follow-up change that belongs to an
existing commit (a typo, a lint fix, a review remark) goes into that commit, not into a new
"fix" commit:
- the last commit: `git commit --amend`
- an earlier one: `git commit --fixup=<sha>`, then `git rebase --autosquash origin/develop`

Once the branch is pushed, rewriting it needs `git push --force-with-lease` (never plain
`--force`, never on `develop`/`main`). Ask the user first, as for any push.

## 2. Dependabot (required by CLAUDE.md)

Run the `triage-dependabot` skill. Merging any non-blocking PR it finds needs the user's
confirmation. If something was merged, it also brings this branch up to date: merge `develop`,
`uv sync` (in `backend/`), lint, test.

## 3. Quality gates

First run the `compliance-audit` skill in quick mode on the branch
(`compliance-audit quick <branch>`). A MUST it flags gets fixed on the branch, or listed in
the PR body under "Pre-PR checks" with a follow-up issue. Don't open the PR while an
unresolved MUST is neither fixed nor listed. If it reports "no compliance-relevant change",
note that in the PR body and move on.

```bash
task lint
task test        # must report 100 % coverage
```

Run `task test-e2e` too if the diff touches `backend/lineup/document/`, `backend/lineup/water_polo/`,
`backend/lineup/api/file_response.py`, `backend/resources/`, `backend/Dockerfile`, `backend/docker/`
or `compose.yml`. It
needs Docker and stops the running `lineup` container at the end; tell the user beforehand.

Check that every new or changed module has tests (CLAUDE.md "Tests" conventions), and that
no new ruff `S` ignores were added outside the two documented spots.

## 4. Docs

Always run the `update-documentation` skill, whatever the diff. It covers `README.md`,
`CLAUDE.md`, the docstrings of the code the diff touches and `documentation/` (the wiki mirror, including the Newcomer Guide and
References pages, and `task docs:references` for the generated block). Commit the result,
after approval.

The PR needs either a docs diff, or a `No doc impact: <reason>` line in the body plus the
`no-docs` label (adding a label is a state-changing `gh` command: ask first). CI's
`Docs updated` check (`scripts/check_docs_touched.sh`) fails otherwise, so run
`scripts/check_docs_touched.sh origin/develop HEAD` yourself before opening the PR.

## 5. Find the linked issues

```bash
gh issue list --repo LasterBergamot/lineup --state open --search "<keywords from the diff>" --json number,title
```

- `Closes #N` only for issues whose **Acceptance** checklist is fully met by this PR.
  PRs #12, #14 and #37 didn't link their issues, which then had to be closed by hand.
- `Refs #N` for partial progress. Say in the body which part is done.

## 6. Open the PR

```bash
git push -u origin <branch>
gh pr create --repo LasterBergamot/lineup --base develop --head <branch> --title "<imperative summary>" --body-file - <<'EOF'
## Summary
- **What changed**, and the *why* (the bug or need it addresses)

Closes #N / Refs #M (what part)

## Pre-PR checks
- Dependabot alerts: …
- Dependabot PRs: … (merged / blocking + reason)

## Docs
- Updated: … (README / CLAUDE.md / documentation pages), or `No doc impact: <reason>`

## Test plan
- [x] `task lint`
- [x] `task test` (N passed, 100 % coverage)
- [x] `task test-e2e` (if applicable)
- [ ] Post-merge checks, if any (e.g. wiki-sync run)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

End the body with the attribution line the current session's system reminder specifies,
if there is one.

## 7. Watch CI

```bash
gh pr checks <n> --repo LasterBergamot/lineup --watch --interval 20
```

Report the PR URL and the check results. If a check fails, read the log
(`gh run view <id> --log-failed`) and propose a fix. Never merge the PR yourself unless the
user explicitly asks.

When the user asks to merge, use a **merge commit**, never squash or rebase:

```bash
gh pr merge <n> --repo LasterBergamot/lineup --merge
```

Squash and rebase merges create new commits. The branch's own commits (and their `#N`
references) then never reach `develop`, and `git branch -d` refuses to delete the merged
branch. The remote branch is deleted automatically on merge (repo setting). Delete the local
one with `git branch -d <branch>` after `git pull` on `develop`.
