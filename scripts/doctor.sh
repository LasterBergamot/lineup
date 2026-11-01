#!/usr/bin/env bash
# Checks that the tools this repo needs are installed and new enough (`task doctor`).
#
# Required tools fail the run; optional ones are only reported. Version floors match the
# README's Prerequisites: Python 3.13+ (backend/pyproject.toml `requires-python`) and Docker
# Compose 2.24+ (compose.yml uses `env_file` with `required: false`). Node.js and pnpm are
# required too: the `task fe:*` targets need them, and CI uses the current LTS (no floor here).
# So is the GitHub CLI: issues, PRs, CI watching and the Dependabot triage all go through `gh`.
# Exit status: 0 when every required tool is present and new
# enough, 1 otherwise.
set -uo pipefail

failed=0

# version_ge A B: true when dotted version A >= B (numeric compare per field).
version_ge() {
  local IFS=.
  local -a a=($1) b=($2)
  local i
  for ((i = 0; i < ${#b[@]}; i++)); do
    local x=${a[i]:-0} y=${b[i]:-0}
    ((10#$x > 10#$y)) && return 0
    ((10#$x < 10#$y)) && return 1
  done
  return 0
}

# first_version TEXT: the first dotted number (e.g. 3.13.2) in TEXT.
first_version() {
  grep -oE '[0-9]+(\.[0-9]+)+' <<<"$1" | head -n1
}

# check KIND NAME MIN CMD...: run CMD, extract a version, compare with MIN (empty = any).
check() {
  local kind=$1 name=$2 min=$3
  shift 3
  local out version
  if ! out=$("$@" 2>&1); then
    if [[ $kind == required ]]; then
      printf 'FAIL  %-15s not found (required)\n' "$name"
      failed=1
    else
      printf 'skip  %-15s not found (optional)\n' "$name"
    fi
    return
  fi
  version=$(first_version "$out")
  if [[ -n $min ]] && ! version_ge "${version:-0}" "$min"; then
    if [[ $kind == required ]]; then
      printf 'FAIL  %-15s %s is older than %s\n' "$name" "${version:-unknown}" "$min"
      failed=1
    else
      printf 'old   %-15s %s is older than %s (optional)\n' "$name" "${version:-unknown}" "$min"
    fi
    return
  fi
  printf 'ok    %-15s %s\n' "$name" "${version:-present}"
}

echo "Required:"
check required python3 3.13 python3 --version
check required uv "" uv --version
# Arch Linux packages Task as `go-task` (usually aliased to `task`, but aliases don't reach scripts).
task_bin=$(command -v task || command -v go-task || echo task)
check required task "" "$task_bin" --version
check required docker "" docker --version
check required "docker compose" 2.24 docker compose version
check required node "" node --version
check required pnpm "" pnpm --version
check required gh "" gh --version

echo "Optional:"
check optional yamllint "" yamllint --version
check optional actionlint "" actionlint --version
check optional lazydocker "" lazydocker --version

if ((failed)); then
  echo "Missing or outdated required tools. Install links: README.md, section Prerequisites."
  exit 1
fi
echo "All required tools are present."
