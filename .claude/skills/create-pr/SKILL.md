---
name: create-pr
description: Prepare and open a pull request for the current branch of LasterBergamot/lineup — Dependabot triage, lint/test/e2e, docs sync, coverage, then a PR with a structured body and Closes/Refs links. Use when the user asks to open, create or raise a PR, or says a branch is ready for review.
model: sonnet
---

`main` is protected: it only changes through PRs that pass `Lint & test` and
`E2E (real PDF conversion)`. This skill gets a branch into that state and opens the PR.

Committing, pushing, merging Dependabot PRs and creating the PR are all state-changing git
or `gh` commands. Show what you're about to do and get an explicit go-ahead for each.
Approving the PR doesn't approve unrelated merges.

## 1. Know what's in the branch

```bash
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

If you're on `main`, stop: propose a branch name first (`fix/…`, `feat/<issue>-…`,
`chore/…`). Uncommitted changes need a commit, which needs approval, before anything else.

## 2. Dependabot (required by CLAUDE.md)

Run the `triage-dependabot` skill. Merging any non-blocking PR it finds needs the user's
confirmation. If something was merged, it also brings this branch up to date: merge `main`,
`uv sync`, lint, test.

## 3. Quality gates

```bash
task lint
task test        # must report 100 % coverage
```

Run `task test-e2e` too if the diff touches `lineup/document/`, `lineup/water_polo/`,
`lineup/api/file_response.py`, `resources/`, the `Dockerfile`, `docker/` or `compose.yml`. It
needs Docker and stops the running `lineup` container at the end; tell the user beforehand.

Check that every new or changed module has tests (CLAUDE.md "Tests" conventions), and that
no new ruff `S` ignores were added outside the two documented spots.

## 4. Docs

If the diff changes the API, data model, tasks, container or dev workflow, run the
`update-documentation` skill. It covers `README.md`, `CLAUDE.md` and `documentation/` (the
wiki mirror). Commit the result, after approval.

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
gh pr create --repo LasterBergamot/lineup --base main --head <branch> --title "<imperative summary>" --body-file - <<'EOF'
## Summary
- **What changed**, and the *why* (the bug or need it addresses)

Closes #N / Refs #M (what part)

## Pre-PR checks
- Dependabot alerts: …
- Dependabot PRs: … (merged / blocking + reason)

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
