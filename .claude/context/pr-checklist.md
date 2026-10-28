# Before creating a PR: Dependabot

Used by the `create-pr` and `triage-dependabot` skills.

- Before creating a PR in this repo, check for open GitHub Dependabot alerts via `gh api repos/LasterBergamot/lineup/dependabot/alerts` (filter for `"state": "open"`) and surface any findings to the user.
- Also check the open Dependabot version-update PRs (`gh pr list --state open --author "app/dependabot"`, then `gh pr checks <n>` / `gh pr view <n>` for each). Alerts and these PRs are separate: an empty alerts list says nothing about pending PRs. A PR is **blocking** if its CI checks fail, it has merge conflicts, or it is a major-version bump (or touches a core dependency such as SQLAlchemy, FastAPI or asyncpg) whose effect on the current branch's code can't be shown to be safe; otherwise it is **non-blocking**.
  - Non-blocking PRs: list them for the user, and once the user confirms (merging is a state-changing `gh` command, so the usual confirmation rule still applies), merge them, then bring the current branch up to date with the updated `develop` (merge `develop` into it, resolving `backend/pyproject.toml`/`backend/uv.lock` conflicts), run `uv sync` (in `backend/`), and re-run `task lint` and `task test` before creating the PR.
  - Blocking PRs: don't merge them. Report each with the reason (failing check, conflict, breaking change) and discuss the next step with the user.
