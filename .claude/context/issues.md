# Issue conventions

Read by the `new-issue` skill (from `ai-common`), and by `repo-audit` and `compliance-audit`
when they draft issues. The skill holds the procedure; this file holds the project's values.

- **Repo:** `LasterBergamot/lineup` (`$REPO`; `$OWNER` = `LasterBergamot`, `$NAME` = `lineup`).

## Issue forms

`.github/ISSUE_TEMPLATE/` holds three forms (`bug.yml`, `feature.yml`, `chore.yml`) with the
Problem / Evidence / Proposal / Acceptance sections plus Area and Priority dropdowns, and
`config.yml` switches blank issues off. A form can only set fixed labels, so it applies the
`type:*` label and leaves the `area:*`, `priority:*` and `plan:*` labels, the milestone, the
board fields and the parent epic to the maintainer (the `new-issue` skill does all of that, so
prefer it when Claude files the issue). Keep the section names in step with this file.

## Body extras

- `## Privacy & security`: add it to feature and security issues that touch personal data,
  auth, endpoints, external services, logging, files or FE storage/headers. Fill it in with
  `compliance-audit quick <issue#>`; the IDs (e.g. `G4, S8`) come from
  `.claude/skills/compliance-audit/requirements.md`. Leave it out when the quick check finds
  nothing compliance-relevant.
- Audit-made issues end with a marker line: `_Found in the <Mon YYYY> repository audit._`
  (or `compliance audit`).

## Labels

- Exactly one `type:*`: bug, feature, chore, docs, security, epic.
- One or more `area:*`: api, db, auth, pdf, infra, ci, frontend, tooling, docs.
- One `priority:*`: `p0` fix now, `p1` next up, `p2` when convenient.
- One `plan:*` (scope triage, Oct 2026): `plan:keep` (needed for the dev/test preview),
  `plan:keep-cheap` (keep, small effort), `plan:defer` (later; goes in *Mx – Parked*),
  `plan:drop` (not planned; close as not planned).

## Milestones

- `M1 – Hardening`: bugs, data layer, container, CI, tooling.
- `M3 – Dev preview`: Google sign-in, teams and invitations, the frontend, dev deployment
  (`PLAN.md`).
- `Mx – Parked`: deliberately not planned now, prod items included. Issues stay open.
- `M2 – Prod` is closed: no prod environment is planned (`PLAN.md` D1).

Leave the milestone empty only for true backlog.

## Parent epics

#41 API, #42 test/CI, #43 data/Supabase, #44 container/PDF, #45 observability (parked),
#46 tooling, #20 frontend, #92 privacy & security compliance. (#40 auth is closed.) Check that
an epic is still open before linking; add new epics if the set changed.

## Board

- Project **#4** (owner `LasterBergamot`). Its **Auto-add** workflow puts new issues on the
  board by itself.
- Fields: Area (same values as the `area:*` labels), Priority (P0, P1, P2),
  Size (S ≤ half a day, M ≤ 2 days, L bigger), Status (`Todo` for new issues).

## Gotchas seen here

- Auth work moved from #6 to #39: fix stale `#N` references when replacing a body.
- #8 was once left "blocked by" a closed issue: clean up relationships when a blocker closes.
