#!/usr/bin/env bash
# Fails when a change touches code/config paths but none of README.md, CLAUDE.md or
# documentation/. Usage: scripts/check_docs_touched.sh [base-ref] [head-ref]
# Escape hatch: PR_LABELS (comma-separated) containing "no-docs".
set -euo pipefail

base="${1:-origin/develop}"
head="${2:-HEAD}"

code_re='^(backend/(lineup/|alembic/|app\.py$|main\.py$|pyproject\.toml$|Dockerfile$|\.env\.example$)|frontend/src/|scripts/|compose\.yml$|Taskfile\.yml$|\.github/workflows/)'
docs_re='^(README\.md$|CLAUDE\.md$|documentation/)'

if [[ ",${PR_LABELS:-}," == *",no-docs,"* ]]; then
  echo "Label 'no-docs' is set: skipping the docs check."
  exit 0
fi

changed="$(git diff --name-only "${base}...${head}")"

if ! grep -Eq "$code_re" <<<"$changed"; then
  echo "No code or config paths changed: nothing to document."
  exit 0
fi

if grep -Eq "$docs_re" <<<"$changed"; then
  echo "Code and docs both changed: OK."
  exit 0
fi

echo "This change touches code or config but none of README.md, CLAUDE.md or documentation/." >&2
echo "Update the docs (see the update-documentation skill), or, if nothing needs documenting," >&2
echo "add the 'no-docs' label and put 'No doc impact: <reason>' in the PR description." >&2
echo >&2
echo "Code paths changed:" >&2
grep -E "$code_re" <<<"$changed" | sed 's/^/  /' >&2
exit 1
