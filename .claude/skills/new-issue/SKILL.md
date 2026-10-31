---
name: new-issue
description: Create or update a GitHub issue following the project's issue conventions — Problem/Evidence/Proposal/Acceptance body, type/area/priority labels, milestone, project board fields, parent epic and blocked-by relationships. Use when asked to file, open, track or restructure an issue, or to link issues together.
model: haiku
---

Every issue in the project carries the same metadata, so the board and milestones stay
trustworthy. The project's own values (repo, labels, milestones, epics, board) live in
**`.claude/context/issues.md`**. Read it first; this skill only holds the procedure. If the
file is missing, ask the user for the repo and labels instead of guessing, and offer to create
the file from `ai-common`'s template.

Draft first, show the draft to the user, and run the `gh` writes only after an explicit
go-ahead. Creating, editing, linking and closing issues are all state-changing.

Below, `$REPO` is the `owner/name` from the context file, and `$OWNER` / `$NAME` its two parts.

## 1. Draft the body

```markdown
## Problem
What's wrong or missing, and why it matters (one short paragraph).

## Evidence
- `path/to/file:12-34`: what the code does (quote briefly)
- related issues/PRs: #N

## Proposal
- Concrete change(s)

## Acceptance
- [ ] Observable, testable outcome(s)
```

Add the extra sections the context file asks for (for example a privacy or security section,
or an audit marker line). Epics use `## Goal` + `## Sub-issues` instead; their children are
linked as GitHub sub-issues, not as a checklist.

Before drafting, search for duplicates:

```bash
gh issue list --repo $REPO --state all --search "<keywords>"
```

## 2. Pick the metadata

Look the current sets up instead of assuming them, then compare them with the context file:

```bash
gh label list --repo $REPO
gh api repos/$REPO/milestones
```

- **Labels:** follow the label scheme in the context file (typically exactly one `type:*`,
  one or more `area:*`, one `priority:*`, plus any planning labels it defines).
- **Milestone:** pick by the milestone meanings in the context file. Leave it empty only for
  true backlog.
- **Parent epic:** from the epic list in the context file. Check the epic is still open.
- **Board fields:** from the board section of the context file (Status for new issues is
  usually `Todo`).

## 3. Create

```bash
gh issue create --repo $REPO --title "<title>" \
  --label "<labels>" --milestone "<milestone>" --body-file - <<'BODY'
...body...
BODY
```

If the board has an auto-add workflow (the context file says), the issue lands on it by
itself. Set the fields as in step 5.

## 4. Relationships (GraphQL, using node ids)

```bash
node() { gh api repos/$REPO/issues/$1 --jq .node_id; }
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
gh api graphql -f query='{repository(owner:"'$OWNER'",name:"'$NAME'"){issue(number:N){parent{number} blockedBy(first:20){nodes{number}} blocking(first:20){nodes{number}}}}}'
```

When a blocker closes, check that nothing still points at it as an open dependency in a way
that misleads.

## 5. Board fields

With `$PROJECT` the board number from the context file:

```bash
PID=$(gh project view $PROJECT --owner $OWNER --format json --jq .id)
ITEM=$(gh project item-add $PROJECT --owner $OWNER --url https://github.com/$REPO/issues/N --format json --jq .id)  # idempotent
gh project field-list $PROJECT --owner $OWNER --format json   # field ids + option ids
gh project item-edit --id "$ITEM" --project-id "$PID" --field-id <FIELD_ID> --single-select-option-id <OPTION_ID>
```

Skip this step if the context file says the project has no board.

## 6. Editing existing issues

- Body changes: prefer appending a dated section (`## Status (Mon YYYY)`, `## Decision (…)`)
  over rewriting history. When you do replace a body, keep the original intent and fix stale
  `#N` references.
- Closing as done: `gh issue close N --repo $REPO --reason completed --comment "<what resolved it>"`.
  As a duplicate or dropped: `--reason "not planned"`, and link the surviving issue.
- PRs that resolve an issue should say `Closes #N` so GitHub closes it automatically.

## 7. Verify

```bash
gh issue view N --repo $REPO --json labels,milestone,projectItems
```

Report the issue URL plus its labels, milestone, parent, blockers and board fields.
