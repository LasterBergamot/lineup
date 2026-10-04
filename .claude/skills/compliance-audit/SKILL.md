---
name: compliance-audit
description: Check the lineup repo against GDPR, the Hungarian data-protection rules and the OWASP security baseline (requirements.md), then reconcile the gaps with GitHub issues. Use when asked about GDPR, privacy, compliance, security standards, leaking personal data or secrets, or before going public or inviting users. `quick <issue#|branch>` is a lightweight per-feature check, run when implementation of a feature starts and again before its PR.
model: opus
effort: high
---

The requirements are in `requirements.md`, next to this file. It holds the IDs G1–G14 (GDPR),
S1–S15 (security) and H1–H4 (Hungary), each with MUST/SHOULD, a source and where to check.
The requirements file is the single checklist for both modes. Don't restate it here.

The role model is in `requirements.md`: clubs are controllers, we are their processor, and
we are the controller for user accounts. None of this is legal advice. Flag ⚖ items for a
lawyer instead of settling them.

**Read-only until the user approves.** Every git or `gh` write needs an explicit go-ahead,
stage by stage. That is the rule in the user's global CLAUDE.md; approving the plan isn't approval.

## Q. Quick mode: `compliance-audit quick <issue#|branch>`

Use it when implementation of a feature or fix starts (a CLAUDE.md rule) and as a `create-pr`
gate. Single pass, no subagents, no GitHub writes.

1. **Read the change.**
   - For an issue: `gh issue view N --repo LasterBergamot/lineup`, plus the plan if one exists.
   - For a branch: `git diff origin/develop...HEAD`.
2. **Classify.** Match the change against the *Quick-mode triggers* table in `requirements.md`.
   If nothing triggers, say "no compliance-relevant change" and stop.
3. **Check** only the triggered IDs against the change, and against the code it touches.
4. **Report** as a short table: `ID | OK / needs … / N-A | evidence file:line`.
5. **Act.**
   - At issue start: propose `## Privacy & security` acceptance items for the issue. Adding
     them is an issue edit, so ask first. Fold them into the plan and the tests.
   - At PR time: an unresolved MUST either gets fixed on the branch, or is listed in the PR
     body with a follow-up issue. `create-pr` stops until one of the two is done.

## Full audit

### 1. Context

- Read `CLAUDE.md` and `PLAN.md`, `documentation/Privacy-and-Security.md` if it exists, and
  epic #92 with its sub-issues.
- Search the issues for "compliance audit" to find what is already tracked. `repo-audit`
  covers general bugs and drift; this skill covers only the regulatory and standards checks.

### 2. Refresh the requirements

Follow *Refreshing this file* in `requirements.md`. Check the sources with WebFetch (or
WebSearch if it's available). If anything changed (a new OWASP edition, the DPF status, a
processor URL), update the table and **Last reviewed**. That edit is a repo change and goes
into the PR.

### 3. Fan out: three parallel Explore agents

Launch all three in **one message**. Each one is read-only, gets `requirements.md` pasted
into its prompt, and reports `requirement ID | file:line | short quote | why | severity`.
None of them may ever read `.env` files: only `.env.example`, and use `git log -S` without
printing values.

- **Backend.** `backend/app.py`, `main.py`, `lineup/**`, `alembic/**`, `tests/**`, `pyproject.toml`,
  `Dockerfile`, `.dockerignore`, `.env.example`. Also look at the committed fixtures and
  resources (`unzip -p <docx> word/document.xml`) for personal data.
- **Infra, CI, docs and FE.** `.github/**`, `compose.yml`, `Taskfile.yml`, `.gitignore`,
  `.claude/settings.json`, `documentation/*`, `README.md`, `PLAN.md`, and `frontend/**`
  (headers, fonts, storage, third-party requests). Check the git history for committed secrets.
- **GitHub state.** Read-only `gh` only:
  - issues touching the requirement areas;
  - `gh api repos/LasterBergamot/lineup --jq .security_and_analysis`;
  - open code-scanning, secret-scanning and Dependabot alerts;
  - branch protection.

### 4. Verify

For every MUST that fails, read the cited lines yourself and reproduce the problem where that
is cheap. Drop or downgrade whatever doesn't hold up. Mark what you reproduced as **[verified]**.

### 5. Compliance matrix (the plan file)

- **Matrix:** one row per requirement: `ID | pass / partial / fail / N-A | evidence | issue #N`.
  This makes audits comparable over time.
- **Gaps:** grouped, each mapped to an existing issue if one covers it, otherwise to a proposed
  new one. An existing issue keeps its parent epic; list it under #92's "Related" instead of
  re-parenting it.
- **Drafts:**
  - New issues: Problem / Evidence / Proposal / Acceptance.
  - Changes to existing issues: a dated `## Compliance (<Mon YYYY>)` section.
  - Every issue body ends with `Found in the <Mon YYYY> compliance audit.`

Ask the user only the questions that change the outcome. One example is the role model, if
it no longer matches.

### 6. Apply (after approval, each stage confirmed)

Use the `new-issue` skill's recipes. Keep the drafts and the created numbers in a scratch dir
outside the repo, e.g. `/tmp/compliance-audit/`, so a failed stage can be resumed. Stages:

1. create issues
2. sub-issue and blocked-by links
3. board fields
4. amendments to existing issues

`requirements.md` edits go through a branch and `create-pr`.

Finish with a read-only check: each new issue has labels, a milestone, the right parent and
its board fields.
