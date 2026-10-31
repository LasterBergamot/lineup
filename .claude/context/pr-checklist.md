# Before and while creating a PR

Read by the `create-pr` and `triage-dependabot` skills (from `ai-common`). The skills hold
the procedure; this file holds the project's rules and values.

## Repo and branches

- **Repo:** `LasterBergamot/lineup`. **Base branch:** `develop` (the default; deploys to dev).
  `main` is the release line and only changes through a `develop` → `main` PR or a hotfix.
- **Branch names:** `fix/…`, `feat/<issue>-…`, `chore/<issue>-…`, `docs/…`.
- **Protected:** `develop` and `main` change only through PRs that pass `Lint & test` and
  `E2E (real PDF conversion)`, plus `Docs updated` for PRs.
- **Merge method:** a merge commit (`gh pr merge <n> --repo LasterBergamot/lineup --merge`),
  never squash or rebase, so each branch commit and its `#N` reference reaches `develop` and
  `git branch -d` works afterwards. GitHub deletes the remote branch on merge.
- **Commit subjects:** `#N - <imperative summary>`.

## Dependabot

- Before creating a PR, check for open Dependabot alerts via `gh api repos/LasterBergamot/lineup/dependabot/alerts` (filter for `"state": "open"`) and surface any findings to the user.
- Also check the open Dependabot version-update PRs (`gh pr list --state open --author "app/dependabot"`, then `gh pr checks <n>` / `gh pr view <n>` for each). Alerts and these PRs are separate: an empty alerts list says nothing about pending PRs. A PR is **blocking** if its CI checks fail, it has merge conflicts, or it is a major-version bump (or touches a core dependency) whose effect on the current branch's code can't be shown to be safe; otherwise it is **non-blocking**.
  - Non-blocking PRs: list them for the user, and once the user confirms (merging is a state-changing `gh` command, so the usual confirmation rule still applies), merge them, then bring the current branch up to date with the updated `develop` (merge `develop` into it, resolving `backend/pyproject.toml`/`backend/uv.lock` conflicts), run `uv sync` (in `backend/`), and re-run `task lint` and `task test` before creating the PR.
  - Blocking PRs: don't merge them. Report each with the reason (failing check, conflict, breaking change) and discuss the next step with the user.
- **Core dependencies:** SQLAlchemy, FastAPI, asyncpg, pydantic, alembic, python-docx.
- **Lock file:** regenerate with `uv lock` (run from `backend/`), never by hand; then
  `(cd backend && uv sync)`, `task lint`, `task test`.
- **Known recurring cases:**
  - A ruff bump that adds new rule violations is blocking until a dedicated issue fixes them
    (#62; the open bump is PR #149).
  - The `setup-task` API rate limit was an environmental CI failure, fixed on `develop` by
    passing `repo-token` to `arduino/setup-task`: propose `@dependabot rebase`.
  - `wiki-sync.yml` only runs on pushes to `develop`, so a PR's CI never exercises it: an
    action bump that affects it counts as unverified.

## Gates, in order

1. `compliance-audit quick <branch>`. A MUST it flags gets fixed on the branch, or listed in
   the PR body under "Pre-PR checks" with a follow-up issue. If it reports "no
   compliance-relevant change", say so in the PR body.
2. `task lint` (ruff, including the `S` rules and `D1` docstrings). No new ruff `S` ignores
   outside the documented spots (`.claude/rules/backend-security.md`).
3. `task test`: must report 100 % coverage. Every new or changed module has tests
   (`.claude/rules/backend-tests.md`).
4. `task test-e2e` if the diff touches `backend/lineup/document/`, `backend/lineup/water_polo/`,
   `backend/lineup/api/file_response.py`, `backend/resources/`, `backend/Dockerfile`,
   `backend/docker/` or `compose.yml`. It needs Docker and stops the running `lineup`
   container at the end: tell the user first.
5. Frontend changes: `task fe:check`.

## Docs

- Always run the `update-documentation` skill (doc map: `.claude/context/docs.md`).
- The PR needs a docs diff, or a `No doc impact: <reason>` line in the body plus the
  `no-docs` label (adding a label is a state-changing `gh` command: ask first). CI's
  `Docs updated` check fails otherwise; run `scripts/check_docs_touched.sh origin/develop HEAD`
  yourself before opening the PR.
- Use `.github/pull_request_template.md` for the body.

## Issues

- `Closes #N` only when the issue's **Acceptance** checklist is fully met; `Refs #N` for
  partial progress. PRs #12, #14 and #37 didn't link their issues, which then had to be
  closed by hand.
