---
name: new-issue
description: Create or update a GitHub issue in LasterBergamot/lineup following the project's conventions — Problem/Evidence/Proposal/Acceptance body, type/area/priority labels, milestone, "Lineup" project board fields (Status/Area/Priority/Size), parent epic and blocked-by relationships. Use when asked to file, open, track or restructure an issue, or to link issues together.
model: haiku
---

Every issue in this repo carries the same metadata, so the board and milestones stay
trustworthy. Draft first, show the draft to the user, and run the `gh` writes only after an
explicit go-ahead. Creating, editing, linking and closing issues are all state-changing.

## 1. Draft the body

```markdown
## Problem
What's wrong or missing, and why it matters (one short paragraph).

## Evidence
- `path/to/file.py:12-34`: what the code does (quote briefly)
- related issues/PRs: #N

## Proposal
- Concrete change(s)

## Acceptance
- [ ] Observable, testable outcome(s), e.g. "unknown team_id → 404, with tests"

## Privacy & security   <!-- optional, see below -->
- G4, S8: requirement IDs touched, plus the acceptance items they add
```

Add the `## Privacy & security` section to feature and security issues that touch personal
data, auth, endpoints, external services, logging, files or FE storage/headers. Fill it in
with `compliance-audit quick <issue#>`; the IDs come from
`.claude/skills/compliance-audit/requirements.md`. Leave it out when the quick check finds
nothing compliance-relevant.

Epics (`type:epic`) use `## Goal` + `## Sub-issues` instead. Their children are linked as
GitHub sub-issues, not as a checklist.

Before drafting, search for duplicates:

```bash
gh issue list --repo LasterBergamot/lineup --state all --search "<keywords>"
```

## 2. Pick the metadata

Look the current sets up instead of assuming them:

```bash
gh label list --repo LasterBergamot/lineup
gh api repos/LasterBergamot/lineup/milestones
```

- **Labels:** exactly one `type:*` (bug, feature, chore, docs, security, epic), one or more
  `area:*` (api, db, auth, pdf, infra, ci, frontend, tooling, docs), and one `priority:*`:
  - `p0`: fix now
  - `p1`: next up
  - `p2`: when convenient
- **Milestone:**
  - `M1 – Hardening`: bugs, data layer, container, CI, tooling
  - `M2 – Prod`: prod Supabase project, prod CD from `main`, releases, RLS, observability
  - `M3 – Dev preview`: Google sign-in, teams and invitations, the frontend, dev deployment (`PLAN.md`)

  Leave it empty only for true backlog.
- **Parent epic:** #40 auth, #41 API, #42 test/CI, #43 data/Supabase, #44 container/PDF,
  #45 observability, #46 tooling, #20 frontend. Check that these are still open; add new epics if the
  set changed.
- **Board fields:**
  - Area: same values as the `area:*` labels
  - Priority: P0, P1, P2
  - Size: S (≤ half a day), M (≤ 2 days), L (bigger)
  - Status: `Todo` for new issues

## 3. Create

```bash
gh issue create --repo LasterBergamot/lineup --title "<title>" \
  --label "type:bug,area:api,priority:p1" --milestone "M1 – Hardening" --body-file - <<'EOF'
...body...
EOF
```

The board's **Auto-add** workflow puts new issues on project #4 by itself. Set the fields as
shown in step 5 below.

## 4. Relationships (GraphQL, using node ids)

```bash
node() { gh api repos/LasterBergamot/lineup/issues/$1 --jq .node_id; }
# make CHILD a sub-issue of PARENT (replaceParent moves it if it already has one)
gh api graphql -f query='mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c,replaceParent:true}){issue{number}}}' \
  -f p=$(node PARENT) -f c=$(node CHILD)
# ISSUE is blocked by BLOCKER
gh api graphql -f query='mutation($i:ID!,$b:ID!){addBlockedBy(input:{issueId:$i,blockingIssueId:$b}){issue{number}}}' \
  -f i=$(node ISSUE) -f b=$(node BLOCKER)
```

Removal uses `removeSubIssue(input:{issueId,subIssueId})` and
`removeBlockedBy(input:{issueId,blockingIssueId})`. Read the current state first:

```bash
gh api graphql -f query='{repository(owner:"LasterBergamot",name:"lineup"){issue(number:N){parent{number} blockedBy(first:20){nodes{number}} blocking(first:20){nodes{number}}}}}'
```

When a blocker closes, check that nothing still points at it as an *open* dependency in a
way that misleads; #8 was once left "blocked by" a closed issue.

## 5. Board fields

```bash
PID=$(gh project view 4 --owner LasterBergamot --format json --jq .id)
ITEM=$(gh project item-add 4 --owner LasterBergamot --url https://github.com/LasterBergamot/lineup/issues/N --format json --jq .id)  # idempotent
gh project field-list 4 --owner LasterBergamot --format json   # → field ids + option ids for Status/Area/Priority/Size
gh project item-edit --id "$ITEM" --project-id "$PID" --field-id <FIELD_ID> --single-select-option-id <OPTION_ID>
```

## 6. Editing existing issues

- Body changes:
  - **Prefer appending a dated section** (`## Status (Mon YYYY)`, `## Decision (…)`) over
    rewriting history.
  - When you do replace a body, keep the original intent and fix stale `#N` references.
    For example, auth work moved from #6 to #39.
- Closing as done:

  ```bash
  gh issue close N --reason completed --comment "<what resolved it>"
  ```

  As a duplicate: add `--reason "not planned"` and link the surviving issue.
- PRs that resolve an issue should say `Closes #N` so GitHub closes it automatically.

## 7. Verify

```bash
gh issue view N --repo LasterBergamot/lineup --json labels,milestone,projectItems
```

Report the issue URL plus its labels, milestone, parent, blockers and board fields.
