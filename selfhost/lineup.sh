#!/usr/bin/env bash
# lineup.sh - install, update, back up, restore and check a self-hosted Lineup.
#
# Run it from the folder it lives in (the extracted release bundle):
#
#   ./lineup.sh                 numbered menu
#   ./lineup.sh doctor          check that this machine is ready (changes nothing)
#   ./lineup.sh install         first-time setup
#   ./lineup.sh update          move to the newest release, with a backup first
#   ./lineup.sh backup          back up now
#   ./lineup.sh restore         go back to an earlier backup
#   ./lineup.sh status          is it running, when was the last backup, is there a newer release
#
# It needs only bash, Docker (with Compose 2.20 or newer) and curl or wget. Everything it says to the
# operator comes from messages/<language>.sh (Hungarian by default; LINEUP_LANG=en for English), and
# every message says what is happening, what went wrong and what to do next.
#
# Rules this script keeps: it never prints a secret (not on success, not on failure), never uses
# `set -x`, never `source`s a file the operator supplies (`--from-file` is parsed line by line), and
# never touches `.env` or the backup folder when it replaces its own files during an update.
#
# Settings read from the environment, meant for the automated tests only (the plain install uses the
# defaults): LINEUP_ENV_FILE, LINEUP_COMPOSE_FILES (space-separated), LINEUP_PROJECT (Compose project
# name), LINEUP_MEMINFO_FILE, LINEUP_HEALTH_TRIES and LINEUP_HEALTH_SLEEP.
# The cmd_* functions take options when called by name from the command line, and none from the menu.
# shellcheck disable=SC2119,SC2120
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
ENV_FILE="${LINEUP_ENV_FILE:-$DIR/.env}"
COMPOSE_FILES="${LINEUP_COMPOSE_FILES:-$DIR/compose.yml}"
MEMINFO_FILE="${LINEUP_MEMINFO_FILE:-/proc/meminfo}"

REPO="LasterBergamot/lineup"
# Not `/releases/latest`: that endpoint skips pre-releases, and every release before 1.0 is one.
RELEASES_URL="https://api.github.com/repos/$REPO/releases?per_page=1"
DOWNLOAD_URL="https://github.com/$REPO/releases/download"
IMAGE_PREFIX="ghcr.io/lasterbergamot/lineup-api"
# What a release bundle holds that this script manages (never `.env`, `backups/` or `previous/`).
BUNDLE_ITEMS=(lineup.sh compose.yml postgres-init backup messages VERSION)

umask 022
TMP_PATHS=()

cleanup() {
  local path
  for path in "${TMP_PATHS[@]+"${TMP_PATHS[@]}"}"; do
    rm -rf "$path"
  done
}
trap cleanup EXIT

# --- messages --------------------------------------------------------------------------------

# The value of NAME in the .env file ("" when absent). The file is read as text, never sourced.
get_env() {
  local line value
  [ -f "$ENV_FILE" ] || return 0
  line="$(grep -m1 "^$1=" "$ENV_FILE" || true)"
  value="${line#*=}"
  value="${value#\'}"
  value="${value%\'}"
  printf '%s' "$value"
}

load_language() {
  local code="${LINEUP_LANG:-}"
  if [ -z "$code" ]; then
    code="$(get_env LINEUP_LANG)"
  fi
  case "$code" in
    hu | en) ;;
    *) code=hu ;;
  esac
  # shellcheck source=/dev/null
  . "$DIR/messages/$code.sh"
}

# Print the message MSG_<key> without a newline; the other arguments fill its %s places.
m() {
  local key="MSG_$1" format
  shift
  format="${!key-}"
  if [ -z "$format" ]; then
    format="$key"
  fi
  # shellcheck disable=SC2059
  printf "$format" "$@"
}

# Ask the person something: the message, then a space, on stderr (so the answer is not mixed into output).
prompt() {
  m "$@" >&2
  printf ' ' >&2
}

# Print a message and a newline. `say_err` is the same on stderr.
say() {
  m "$@"
  printf '\n'
}

say_err() {
  m "$@" >&2
  printf '\n' >&2
}

# Print the backup limits text, wrapped for a terminal.
say_backup_limits() {
  printf '\n'
  m BACKUP_LIMITS | fold -s -w 78
  printf '\n\n'
}

# --- small helpers ---------------------------------------------------------------------------

require_env() {
  if [ ! -f "$ENV_FILE" ]; then
    say_err NOT_INSTALLED
    return 1
  fi
}

# Run docker compose for this install.
dc() {
  local -a args=(--env-file "$ENV_FILE") files
  local file
  IFS=' ' read -r -a files <<<"$COMPOSE_FILES"
  for file in "${files[@]}"; do
    args+=(-f "$file")
  done
  if [ -n "${LINEUP_PROJECT:-}" ]; then
    args+=(-p "$LINEUP_PROJECT")
  fi
  docker compose "${args[@]}" "$@"
}

# Download URL to stdout, or to the file given as $2.
fetch() {
  if command -v curl >/dev/null 2>&1; then
    if [ -n "${2:-}" ]; then
      curl -fsSL --connect-timeout 15 --max-time 300 -o "$2" "$1"
    else
      curl -fsSL --connect-timeout 15 --max-time 60 "$1"
    fi
  elif command -v wget >/dev/null 2>&1; then
    wget -q --timeout=60 -O "${2:--}" "$1"
  else
    return 127
  fi
}

# Set NAME=VALUE in the .env file by writing a private temporary file next to it and renaming it.
set_env() {
  local name="$1" value="$2" tmp line found=0
  tmp="$(mktemp "$ENV_FILE.XXXXXX")"
  TMP_PATHS+=("$tmp")
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "${line%%=*}" = "$name" ]; then
      printf '%s=%s\n' "$name" "$value"
      found=1
    else
      printf '%s\n' "$line"
    fi
  done <"$ENV_FILE" >"$tmp"
  if [ "$found" -eq 0 ]; then
    printf '%s=%s\n' "$name" "$value" >>"$tmp"
  fi
  chmod 600 "$tmp"
  mv "$tmp" "$ENV_FILE"
}

# Free space in kilobytes on the disk holding the path $1 ("" if unknown).
free_kb() {
  df -Pk "$1" 2>/dev/null | awk 'NR == 2 {print $4}'
}

# Read one line from the person into the variable named $1. Hidden when $2 is "hidden".
read_answer() {
  local __reply=""
  if [ "${2:-}" = hidden ]; then
    IFS= read -r -s __reply || true
    if [ -t 0 ]; then
      printf '\n' >&2
    fi
  else
    IFS= read -r __reply || true
  fi
  printf -v "$1" '%s' "$__reply"
}

# Succeeds when the person types the word $1 (upper case; the case they type does not matter).
confirmed_with_word() {
  local answer
  read_answer answer
  answer="$(printf '%s' "$answer" | tr '[:lower:]' '[:upper:]')"
  [ "$answer" = "$1" ]
}

valid_tag() {
  [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]]
}

# The version written in the bundle's VERSION file.
bundle_version() {
  local version=""
  if [ -f "$DIR/VERSION" ]; then
    version="$(tr -d '[:space:]' <"$DIR/VERSION")"
  fi
  printf '%s' "$version"
}

# --- health ----------------------------------------------------------------------------------

# One check of the API, including its database (the Dockerfile's health check, plus ?db=1).
api_healthy() {
  dc exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health?db=1', timeout=10)" \
    >/dev/null 2>&1
}

# Wait up to about two minutes for the API to answer.
wait_healthy() {
  local tries="${LINEUP_HEALTH_TRIES:-24}" pause="${LINEUP_HEALTH_SLEEP:-5}" attempt=1
  while [ "$attempt" -le "$tries" ]; do
    if api_healthy; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -le "$tries" ]; then
      sleep "$pause"
    fi
  done
  return 1
}

# --- backups ---------------------------------------------------------------------------------

backup_folder() {
  local folder
  folder="$(get_env BACKUP_DIR)"
  if [ -z "$folder" ]; then
    folder="$DIR/backups"
  fi
  printf '%s' "$folder"
}

# Create the backup folder (private to its owner) and give it to the user the backup service runs as
# (999, the `postgres` user of the image). Safe to repeat. Only this one command gets the CHOWN
# capability back; the mode is set from the host first, because the container's root has no right to
# change the mode of a folder it does not own (it would need FOWNER).
prepare_backup_folder() {
  local folder
  folder="$(backup_folder)"
  mkdir -p "$folder"
  chmod 700 "$folder" 2>/dev/null || true
  dc run --rm -T --no-deps --user 0 --cap-add CHOWN --entrypoint sh backup \
    -c 'chown 999:999 /backups' >/dev/null
}

# One backup now. Extra arguments go to backup.sh (for example --safety).
backup_once() {
  prepare_backup_folder || return 1
  dc run --rm -T backup --once "$@"
}

# The ids of the restorable backups, one per line: both of their files exist.
backup_ids() {
  local files id
  files="$(dc run --rm -T --no-deps --entrypoint ls backup /backups 2>/dev/null)" || return 1
  while IFS= read -r id; do
    id="${id#lineup-}"
    id="${id%.dump}"
    if grep -qxF "auth-$id.dump" <<<"$files" &&
      [[ "$id" =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2}|safety-[0-9]{8}T[0-9]{6}Z)$ ]]; then
      printf '%s\n' "$id"
    fi
  done < <(printf '%s\n' "$files" | grep -E '^lineup-.*\.dump$' | sort || true)
}

# Show the two newest files in the backup folder with their sizes.
show_backup_files() {
  # The command is for the shell inside the container, so it must reach it unexpanded.
  # shellcheck disable=SC2016
  dc run --rm -T --no-deps --entrypoint sh backup \
    -c 'cd /backups && du -h -- $(ls -t -- *.dump | head -n 2)' 2>/dev/null || true
}

# --- doctor ----------------------------------------------------------------------------------

DOCTOR_WARNINGS=0
DOCTOR_PROBLEMS=0

doctor_ok() {
  printf '  %s %s\n' "$(m TAG_OK)" "$1"
}

doctor_warn() {
  DOCTOR_WARNINGS=$((DOCTOR_WARNINGS + 1))
  printf '  %s %s\n' "$(m TAG_WARN)" "$1"
  printf '        %s\n' "$(m FIX_PREFIX "$2")"
}

doctor_problem() {
  DOCTOR_PROBLEMS=$((DOCTOR_PROBLEMS + 1))
  printf '  %s %s\n' "$(m TAG_PROBLEM)" "$1"
  printf '        %s\n' "$(m FIX_PREFIX "$2")"
}

# Compose is new enough when $1 (for example "2.29.1" or "v5.0.0") is at least 2.20.
compose_version_ok() {
  local version="${1#v}" major minor
  major="${version%%.*}"
  minor="${version#*.}"
  minor="${minor%%.*}"
  [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]] || return 1
  [ "$major" -gt 2 ] || { [ "$major" -eq 2 ] && [ "$minor" -ge 20 ]; }
}

check_architecture() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64 | amd64 | aarch64 | arm64) doctor_ok "$(m DOC_ARCH_OK "$arch")" ;;
    *) doctor_problem "$(m DOC_ARCH_BAD "$arch")" "$(m DOC_ARCH_BAD_FIX)" ;;
  esac
}

check_memory() {
  local kb tenths
  kb="$(awk '/^MemTotal:/ {print $2}' "$MEMINFO_FILE" 2>/dev/null || true)"
  if ! [[ "$kb" =~ ^[0-9]+$ ]]; then
    doctor_warn "$(m DOC_RAM_UNKNOWN)" "$(m DOC_RAM_UNKNOWN_FIX)"
    return
  fi
  tenths=$((kb * 10 / 1048576))
  local text="$((tenths / 10)).$((tenths % 10))"
  if [ "$kb" -lt 1048576 ]; then
    doctor_problem "$(m DOC_RAM_BAD "$text")" "$(m DOC_RAM_BAD_FIX)"
  elif [ "$kb" -lt 2097152 ]; then
    doctor_warn "$(m DOC_RAM_WARN "$text")" "$(m DOC_RAM_WARN_FIX)"
  else
    doctor_ok "$(m DOC_RAM_OK "$text")"
  fi
}

check_disk() {
  local kb gb
  kb="$(free_kb "$DIR")"
  if ! [[ "$kb" =~ ^[0-9]+$ ]]; then
    doctor_warn "$(m DOC_DISK_UNKNOWN)" "$(m DOC_DISK_UNKNOWN_FIX)"
    return
  fi
  gb=$((kb / 1048576))
  if [ "$kb" -lt 10485760 ]; then
    doctor_warn "$(m DOC_DISK_WARN "$gb")" "$(m DOC_DISK_WARN_FIX)"
  else
    doctor_ok "$(m DOC_DISK_OK "$gb")"
  fi
}

check_docker() {
  local info version
  if ! command -v docker >/dev/null 2>&1; then
    doctor_problem "$(m DOC_DOCKER_MISSING)" "$(m DOC_DOCKER_MISSING_FIX)"
    return
  fi
  if info="$(docker info 2>&1)"; then
    doctor_ok "$(m DOC_DOCKER_RUNNING)"
    doctor_ok "$(m DOC_DOCKER_PERMISSION)"
  elif printf '%s' "$info" | grep -qi 'permission denied'; then
    doctor_problem "$(m DOC_DOCKER_DENIED)" "$(m DOC_DOCKER_DENIED_FIX)"
  else
    doctor_problem "$(m DOC_DOCKER_DOWN)" "$(m DOC_DOCKER_DOWN_FIX)"
  fi
  if version="$(docker compose version --short 2>/dev/null)" && compose_version_ok "$version"; then
    doctor_ok "$(m DOC_COMPOSE_OK "${version#v}")"
  elif [ -n "${version:-}" ]; then
    doctor_problem "$(m DOC_COMPOSE_OLD "${version#v}")" "$(m DOC_COMPOSE_FIX)"
  else
    doctor_problem "$(m DOC_COMPOSE_MISSING)" "$(m DOC_COMPOSE_FIX)"
  fi
}

check_network() {
  local code=0
  if command -v curl >/dev/null 2>&1; then
    # Without -f, curl succeeds whenever the server answered, even with "sign in first".
    curl -s -o /dev/null --connect-timeout 10 --max-time 20 https://ghcr.io/v2/ || code=$?
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O /dev/null --timeout=20 https://ghcr.io/v2/ || code=$?
    # wget exits 6 or 8 when the server answered with an error such as "sign in first": it was reached.
    case "$code" in 6 | 8) code=0 ;; esac
  else
    doctor_warn "$(m DOC_FETCH_MISSING)" "$(m DOC_FETCH_MISSING_FIX)"
    return
  fi
  if [ "$code" -eq 0 ]; then
    doctor_ok "$(m DOC_NETWORK_OK)"
  else
    doctor_problem "$(m DOC_NETWORK_BAD)" "$(m DOC_NETWORK_BAD_FIX)"
  fi
}

cmd_doctor() {
  if [ "$#" -gt 0 ]; then
    say_err UNKNOWN_OPTION "$1"
    return 2
  fi
  DOCTOR_WARNINGS=0
  DOCTOR_PROBLEMS=0
  say DOC_TITLE
  check_architecture
  check_memory
  check_disk
  check_docker
  check_network
  printf '\n'
  if [ "$DOCTOR_PROBLEMS" -gt 0 ]; then
    say DOC_SUMMARY_PROBLEMS "$DOCTOR_PROBLEMS"
    return 1
  elif [ "$DOCTOR_WARNINGS" -gt 0 ]; then
    say DOC_SUMMARY_WARNINGS "$DOCTOR_WARNINGS"
  else
    say DOC_SUMMARY_OK
  fi
}

# --- install ---------------------------------------------------------------------------------

IN_URL=""
IN_TUNNEL=""
IN_GOOGLE_ID=""
IN_GOOGLE_SECRET=""
IN_BACKUP_DIR=""
IN_LANG=""
IMAGE=""
SECRET_POSTGRES=""
SECRET_AUTH_DB=""
SECRET_APP=""
SECRET_JWT=""
SECRET_KEYS=""

# The characters a pasted value may hold: enough for URLs, tokens and client ids, and none that
# an .env file or Compose would treat specially (quotes, spaces, `$`, backslashes).
valid_token() {
  [[ "$1" =~ ^[A-Za-z0-9._~:/@+=%,-]+$ ]]
}

valid_url() {
  [[ "$1" =~ ^https://[A-Za-z0-9.-]+(:[0-9]+)?$ ]]
}

valid_folder() {
  [[ "$1" =~ ^/[A-Za-z0-9._/-]*$ ]]
}

# Fill the IN_* variables from a KEY=VALUE file. The file must be private (mode 600) and is parsed,
# never executed.
read_install_file() {
  local file="$1" perm line key value number=0
  if [ ! -f "$file" ]; then
    say_err FILE_MISSING "$file"
    return 1
  fi
  perm="$(stat -c %a "$file" 2>/dev/null || stat -f %Lp "$file" 2>/dev/null || echo unknown)"
  if [ "$perm" != 600 ]; then
    say_err FILE_MODE "$file" "$file"
    return 1
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    number=$((number + 1))
    line="${line%$'\r'}"
    case "$line" in
      '' | '#'*) continue ;;
    esac
    if [[ "$line" != *=* ]]; then
      say_err FILE_BAD_LINE "$number"
      continue
    fi
    key="${line%%=*}"
    value="${line#*=}"
    case "$value" in
      \'*\') value="${value#\'}"; value="${value%\'}" ;;
      \"*\") value="${value#\"}"; value="${value%\"}" ;;
    esac
    case "$key" in
      PUBLIC_URL) IN_URL="$value" ;;
      TUNNEL_TOKEN) IN_TUNNEL="$value" ;;
      GOOGLE_CLIENT_ID) IN_GOOGLE_ID="$value" ;;
      GOOGLE_SECRET) IN_GOOGLE_SECRET="$value" ;;
      BACKUP_DIR) IN_BACKUP_DIR="$value" ;;
      LINEUP_LANG) IN_LANG="$value" ;;
      *) say_err FILE_UNKNOWN_KEY "$number" ;;
    esac
  done <"$file"
}

# Ask for the variable $1 with the prompt message $2 until the validator $3 accepts it (three tries).
# $4 = hidden hides the typing. An empty answer is accepted for "optional" validators only.
ask_valid() {
  local variable="$1" prompt="$2" validator="$3" hidden="${4:-}" tries=0 answer=""
  while [ "$tries" -lt 3 ]; do
    prompt "$prompt"
    read_answer answer "$hidden"
    if [ "$variable" = IN_URL ]; then
      answer="${answer%/}"
    fi
    if "$validator" "$answer"; then
      printf -v "$variable" '%s' "$answer"
      return 0
    fi
    say_err INSTALL_INVALID_VALUE
    tries=$((tries + 1))
  done
  return 1
}

# Random hex secret from the API image (nothing but Docker is needed on the host).
generate_secret() {
  docker run --rm --entrypoint python "$IMAGE" -c "import secrets; print(secrets.token_hex(24))"
}

write_env_file() {
  local version="$1" tmp
  tmp="$(mktemp "$ENV_FILE.XXXXXX")"
  TMP_PATHS+=("$tmp")
  {
    printf '# Written by lineup.sh install. Private: it holds the passwords of this install.\n'
    printf '# Keep a copy somewhere safe and private; without it a restore on a new machine is much harder.\n'
    printf 'LINEUP_VERSION=%s\n' "$version"
    printf 'LINEUP_LANG=%s\n' "$IN_LANG"
    printf 'PUBLIC_URL=%s\n' "$IN_URL"
    printf 'COMPOSE_PROFILES=tunnel\n'
    printf 'TUNNEL_TOKEN=%s\n' "$IN_TUNNEL"
    printf 'POSTGRES_PASSWORD=%s\n' "$SECRET_POSTGRES"
    printf 'AUTH_DB_PASSWORD=%s\n' "$SECRET_AUTH_DB"
    printf 'LINEUP_APP_PASSWORD=%s\n' "$SECRET_APP"
    printf 'AUTH_JWT_SECRET=%s\n' "$SECRET_JWT"
    printf "AUTH_JWT_KEYS='%s'\n" "$SECRET_KEYS"
    printf 'GOOGLE_CLIENT_ID=%s\n' "$IN_GOOGLE_ID"
    printf 'GOOGLE_SECRET=%s\n' "$IN_GOOGLE_SECRET"
    printf 'BACKUP_DIR=%s\n' "$IN_BACKUP_DIR"
    printf 'AUTH_EMAIL_ENABLED=false\n'
  } >"$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$ENV_FILE"
}

cmd_install() {
  local from_file="" accept=0 version
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --from-file)
        if [ "$#" -lt 2 ]; then
          say_err UNKNOWN_OPTION "$1"
          return 2
        fi
        from_file="$2"
        shift 2
        ;;
      --accept-backup-limits)
        accept=1
        shift
        ;;
      *)
        say_err UNKNOWN_OPTION "$1"
        return 2
        ;;
    esac
  done

  if [ -f "$ENV_FILE" ]; then
    say_err INSTALL_ALREADY
    return 1
  fi
  version="$(bundle_version)"
  if ! valid_tag "$version"; then
    say_err INSTALL_NO_VERSION
    return 1
  fi
  IMAGE="$IMAGE_PREFIX:$version"

  # The language comes first, so that everything after it is in the operator's language.
  if [ -n "$from_file" ]; then
    read_install_file "$from_file" || return 1
  else
    printf 'Language / Nyelv (hu/en) [hu]: ' >&2
    read_answer IN_LANG
  fi
  if [ -z "$IN_LANG" ]; then
    IN_LANG="${LINEUP_LANG:-hu}"
  fi
  case "$IN_LANG" in
    hu | en) ;;
    *) IN_LANG=hu ;;
  esac
  LINEUP_LANG="$IN_LANG"
  load_language

  say INSTALL_CHECKING
  cmd_doctor || {
    say_err INSTALL_DOCTOR_FAILED
    return 1
  }

  if [ -z "$from_file" ]; then
    say INSTALL_INTRO
    ask_valid IN_URL INSTALL_ASK_URL valid_url || { say_err INSTALL_GAVE_UP; return 1; }
    ask_valid IN_TUNNEL INSTALL_ASK_TUNNEL valid_token hidden || { say_err INSTALL_GAVE_UP; return 1; }
    ask_valid IN_GOOGLE_ID INSTALL_ASK_GOOGLE_ID valid_token || { say_err INSTALL_GAVE_UP; return 1; }
    ask_valid IN_GOOGLE_SECRET INSTALL_ASK_GOOGLE_SECRET valid_token hidden || { say_err INSTALL_GAVE_UP; return 1; }
    prompt INSTALL_ASK_BACKUP_DIR "$DIR/backups"
    read_answer IN_BACKUP_DIR
  fi

  IN_URL="${IN_URL%/}"
  if [ -z "$IN_BACKUP_DIR" ]; then
    IN_BACKUP_DIR="$DIR/backups"
  fi
  if ! valid_url "$IN_URL"; then
    say_err INSTALL_BAD_URL
    return 1
  fi
  if ! valid_token "$IN_TUNNEL" || ! valid_token "$IN_GOOGLE_ID" || ! valid_token "$IN_GOOGLE_SECRET"; then
    say_err INSTALL_BAD_VALUE
    return 1
  fi
  if ! valid_folder "$IN_BACKUP_DIR"; then
    say_err INSTALL_BAD_FOLDER
    return 1
  fi

  say_backup_limits
  if [ "$accept" -eq 0 ]; then
    prompt INSTALL_TYPE_TO_ACCEPT "$(m CONFIRM_WORD)"
    if ! confirmed_with_word "$(m CONFIRM_WORD)"; then
      say_err INSTALL_NOT_ACCEPTED
      return 1
    fi
  fi

  say INSTALL_GENERATING
  SECRET_POSTGRES="$(generate_secret)" || { say_err INSTALL_IMAGE_FAILED; return 1; }
  SECRET_AUTH_DB="$(generate_secret)" || { say_err INSTALL_IMAGE_FAILED; return 1; }
  SECRET_APP="$(generate_secret)" || { say_err INSTALL_IMAGE_FAILED; return 1; }
  SECRET_JWT="$(generate_secret)" || { say_err INSTALL_IMAGE_FAILED; return 1; }
  SECRET_KEYS="$(docker run --rm --entrypoint python "$IMAGE" -m lineup.auth.signing_key)" ||
    { say_err INSTALL_IMAGE_FAILED; return 1; }
  local secret
  for secret in "$SECRET_POSTGRES" "$SECRET_AUTH_DB" "$SECRET_APP" "$SECRET_JWT"; do
    if ! [[ "$secret" =~ ^[0-9a-f]{48}$ ]]; then
      say_err INSTALL_IMAGE_FAILED
      return 1
    fi
  done
  if [[ "$SECRET_KEYS" == *"'"* || "$SECRET_KEYS" != "["* ]]; then
    say_err INSTALL_IMAGE_FAILED
    return 1
  fi
  write_env_file "$version"
  say INSTALL_ENV_WRITTEN "$ENV_FILE"

  say INSTALL_PREPARING_FOLDER
  prepare_backup_folder || { say_err INSTALL_FOLDER_FAILED "$IN_BACKUP_DIR"; return 1; }

  say INSTALL_STARTING
  if ! dc up -d --wait --wait-timeout 600; then
    say_err INSTALL_START_FAILED
    return 1
  fi
  say INSTALL_WAITING
  if ! wait_healthy; then
    say_err INSTALL_UNHEALTHY
    return 1
  fi
  say INSTALL_DONE "$IN_URL" "$ENV_FILE" "$IN_BACKUP_DIR"
}

# --- backup / restore ------------------------------------------------------------------------

cmd_backup() {
  if [ "$#" -gt 0 ]; then
    say_err UNKNOWN_OPTION "$1"
    return 2
  fi
  require_env || return 1
  say BACKUP_RUNNING
  if ! backup_once; then
    say_err BACKUP_FAILED
    return 1
  fi
  say BACKUP_DONE "$(backup_folder)"
  show_backup_files
}

cmd_restore() {
  local date="" yes=0 ids id answer
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --date)
        if [ "$#" -lt 2 ]; then
          say_err UNKNOWN_OPTION "$1"
          return 2
        fi
        date="$2"
        shift 2
        ;;
      --yes-restore)
        yes=1
        shift
        ;;
      *)
        say_err UNKNOWN_OPTION "$1"
        return 2
        ;;
    esac
  done
  require_env || return 1

  if ! ids="$(backup_ids)"; then
    say_err RESTORE_LIST_FAILED
    return 1
  fi
  if [ -z "$ids" ]; then
    say_err RESTORE_NONE
    return 1
  fi
  if [ -z "$date" ]; then
    say RESTORE_AVAILABLE
    printf '%s\n' "$ids" | sed 's/^/    /'
    prompt RESTORE_ASK_DATE
    read_answer answer
    date="$answer"
  fi
  if ! grep -qxF -- "$date" <<<"$ids"; then
    say_err RESTORE_UNKNOWN_DATE
    printf '%s\n' "$ids" | sed 's/^/    /' >&2
    return 1
  fi

  say RESTORE_WARNING "$date"
  if [ "$yes" -eq 0 ]; then
    prompt RESTORE_TYPE_TO_CONFIRM "$(m RESTORE_WORD)"
    if ! confirmed_with_word "$(m RESTORE_WORD)"; then
      say_err RESTORE_NOT_CONFIRMED
      return 1
    fi
  fi

  say RESTORE_SAFETY
  if ! backup_once --safety; then
    say_err RESTORE_SAFETY_FAILED
    return 1
  fi

  say RESTORE_STOPPING
  dc stop web api auth >/dev/null || true
  local database
  for database in lineup auth; do
    say RESTORE_DATABASE "$database"
    # Single transaction: if it fails, that database is left as it was. No --no-owner: the roles
    # `lineup_app` and `supabase_auth_admin` must keep their rights on what is restored.
    if ! dc run --rm -T --no-deps --entrypoint pg_restore backup \
      --clean --if-exists --single-transaction --dbname "$database" "/backups/$database-$date.dump" >/dev/null; then
      say_err RESTORE_FAILED "$database" "$date"
      return 1
    fi
  done

  say RESTORE_STARTING
  if ! dc up -d --wait --wait-timeout 600 || ! wait_healthy; then
    say_err RESTORE_UNHEALTHY
    return 1
  fi
  say RESTORE_DONE "$date"
}

# --- update ----------------------------------------------------------------------------------

# The tag of the newest release (pre-releases included).
newest_release() {
  local json tag
  json="$(fetch "$RELEASES_URL")" || return 1
  tag="$(printf '%s' "$json" |
    sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | sed -n '1p')"
  valid_tag "$tag" || return 1
  printf '%s' "$tag"
}

# The database's current Alembic revision ("" when none). Fails when it cannot be read.
alembic_revision() {
  local out
  out="$(dc run --rm -T --no-deps --entrypoint alembic migrate current 2>/dev/null)" || return 1
  printf '%s\n' "$out" | sed -n 's/^\([0-9a-zA-Z_]\{6,\}\)\( (.*)\)\{0,1\}$/\1/p' | sed -n '1p'
}

# Check a downloaded bundle against its checksum file (both in the folder $1).
verify_bundle() {
  local folder="$1" name="$2"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$folder" && sha256sum -c "$name.sha256" >/dev/null 2>&1)
  else
    (cd "$folder" && shasum -a 256 -c "$name.sha256" >/dev/null 2>&1)
  fi
}

# Unpack the bundle $1 into the folder $2 (without its top folder), after checking its paths.
unpack_bundle() {
  local archive="$1" target="$2" listing
  listing="$(tar -tzf "$archive")" || return 1
  if grep -qE '(^/|(^|/)\.\.(/|$))' <<<"$listing"; then
    return 1
  fi
  if grep -qvE '^selfhost(/|$)' <<<"$listing"; then
    return 1
  fi
  mkdir -p "$target"
  tar -xzf "$archive" -C "$target" --strip-components=1
  rm -rf "$target/.env" "$target/backups" "$target/previous"
  [ -f "$target/compose.yml" ] && [ -f "$target/VERSION" ]
}

# Put the files of the bundle folder $1 in place. Single files are replaced by renaming a copy over
# them, which is safe even for this running script (bash keeps reading the old file).
install_files() {
  local from="$1" item
  for item in "${BUNDLE_ITEMS[@]}"; do
    [ -e "$from/$item" ] || continue
    if [ -d "$from/$item" ]; then
      rm -rf "${DIR:?}/$item.new"
      cp -R "$from/$item" "$DIR/$item.new"
      rm -rf "${DIR:?}/$item"
      mv "$DIR/$item.new" "$DIR/$item"
    else
      cp "$from/$item" "$DIR/.$item.new"
      mv "$DIR/.$item.new" "$DIR/$item"
    fi
  done
  chmod -R u+rwX,go+rX "$DIR/backup" "$DIR/postgres-init" "$DIR/messages" 2>/dev/null || true
  chmod 755 "$DIR/lineup.sh" "$DIR/backup/backup.sh" 2>/dev/null || true
}

save_previous() {
  local item
  rm -rf "${DIR:?}/previous"
  mkdir "$DIR/previous"
  for item in "${BUNDLE_ITEMS[@]}"; do
    if [ -e "$DIR/$item" ]; then
      cp -R "$DIR/$item" "$DIR/previous/$item"
    fi
  done
}

# The new version did not start. Undo it when the database was not changed, otherwise explain.
# Arguments: old version, revision before the update, 1 when `up` was started.
update_failed() {
  local old="$1" before="$2" up_started="$3" after="" changed=0
  say_err UPDATE_FAILED
  if [ "$up_started" -eq 1 ]; then
    if after="$(alembic_revision)"; then
      [ "$after" = "$before" ] || changed=1
    else
      changed=1
    fi
  fi
  if [ "$changed" -eq 1 ]; then
    say_err UPDATE_DB_CHANGED "$(date -u +%F)" "$(date -u +%F)" "$old"
    return 1
  fi
  install_files "$DIR/previous"
  set_env LINEUP_VERSION "$old"
  if dc up -d --wait --wait-timeout 600 >/dev/null && wait_healthy; then
    say_err UPDATE_UNDONE "$old"
  else
    say_err UPDATE_UNDONE_BUT_DOWN "$old" "$(date -u +%F)"
  fi
  return 1
}

cmd_update() {
  local target="" current work before up_started=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --version)
        if [ "$#" -lt 2 ]; then
          say_err UNKNOWN_OPTION "$1"
          return 2
        fi
        target="$2"
        shift 2
        ;;
      *)
        say_err UNKNOWN_OPTION "$1"
        return 2
        ;;
    esac
  done
  require_env || return 1
  current="$(get_env LINEUP_VERSION)"

  if [ -n "$target" ]; then
    if ! valid_tag "$target"; then
      say_err UPDATE_BAD_VERSION "$target"
      return 1
    fi
  else
    say UPDATE_LOOKING
    if ! target="$(newest_release)"; then
      say_err UPDATE_NO_RELEASE
      return 1
    fi
  fi
  if [ "$target" = "$current" ]; then
    say UPDATE_CURRENT "$current"
    return 0
  fi

  say UPDATE_DOWNLOADING "$target"
  work="$(mktemp -d "$DIR/.update.XXXXXX")"
  TMP_PATHS+=("$work")
  local name="selfhost-$target.tar.gz"
  if ! fetch "$DOWNLOAD_URL/$target/$name" "$work/$name" ||
    ! fetch "$DOWNLOAD_URL/$target/$name.sha256" "$work/$name.sha256"; then
    say_err UPDATE_DOWNLOAD_FAILED "$target"
    return 1
  fi
  if ! verify_bundle "$work" "$name"; then
    say_err UPDATE_CHECKSUM "$target"
    return 1
  fi
  if ! unpack_bundle "$work/$name" "$work/new" || [ "$(tr -d '[:space:]' <"$work/new/VERSION")" != "$target" ]; then
    say_err UPDATE_BAD_BUNDLE "$target"
    return 1
  fi

  say UPDATE_BACKUP
  if ! backup_once; then
    say_err UPDATE_BACKUP_FAILED
    return 1
  fi
  if ! before="$(alembic_revision)"; then
    say_err UPDATE_REVISION_FAILED
    return 1
  fi

  say UPDATE_INSTALLING "$target"
  save_previous
  install_files "$work/new"
  set_env LINEUP_VERSION "$target"

  say UPDATE_STARTING
  if dc pull && up_started=1 && dc up -d --wait --wait-timeout 600 && wait_healthy; then
    say UPDATE_DONE "$target"
  else
    update_failed "$current" "$before" "$up_started"
  fi
}

# --- status ----------------------------------------------------------------------------------

cmd_status() {
  local problems=0 stamp age_hours newest folder kb path
  if [ "$#" -gt 0 ]; then
    say_err UNKNOWN_OPTION "$1"
    return 2
  fi
  require_env || return 1
  say STATUS_TITLE
  dc ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}' || true
  printf '\n'

  if api_healthy; then
    doctor_ok "$(m STATUS_HEALTH_OK)"
  else
    doctor_problem "$(m STATUS_HEALTH_BAD)" "$(m STATUS_HEALTH_BAD_FIX)"
    problems=1
  fi

  stamp="$(dc run --rm -T --no-deps --entrypoint cat backup /backups/last-success 2>/dev/null || true)"
  stamp="$(printf '%s' "$stamp" | tr -d '[:space:]')"
  if [[ "$stamp" =~ ^[0-9]+$ ]]; then
    age_hours=$((($(date +%s) - stamp) / 3600))
    if [ "$age_hours" -gt 36 ]; then
      doctor_warn "$(m STATUS_BACKUP_OLD "$age_hours")" "$(m STATUS_BACKUP_OLD_FIX)"
    else
      doctor_ok "$(m STATUS_BACKUP_OK "$age_hours")"
    fi
  else
    doctor_warn "$(m STATUS_BACKUP_NONE)" "$(m STATUS_BACKUP_NONE_FIX)"
  fi

  folder="$(backup_folder)"
  for path in "$DIR" "$folder"; do
    kb="$(free_kb "$path")"
    if [[ "$kb" =~ ^[0-9]+$ ]]; then
      if [ "$kb" -lt 10485760 ]; then
        doctor_warn "$(m STATUS_DISK_LOW "$path" "$((kb / 1048576))")" "$(m DOC_DISK_WARN_FIX)"
      else
        doctor_ok "$(m STATUS_DISK_OK "$path" "$((kb / 1048576))")"
      fi
    fi
  done

  say STATUS_VERSION "$(get_env LINEUP_VERSION)"
  if newest="$(newest_release)"; then
    if [ "$newest" = "$(get_env LINEUP_VERSION)" ]; then
      say STATUS_UP_TO_DATE
    else
      say STATUS_NEWER "$newest"
    fi
  else
    say STATUS_RELEASE_UNKNOWN
  fi
  return "$problems"
}

# --- menu and entry point --------------------------------------------------------------------

cmd_menu() {
  local choice=""
  say MENU_TITLE
  say MENU_DOCTOR
  say MENU_INSTALL
  say MENU_UPDATE
  say MENU_BACKUP
  say MENU_RESTORE
  say MENU_STATUS
  say MENU_EXIT
  prompt MENU_PROMPT
  read_answer choice
  case "$choice" in
    1) cmd_doctor ;;
    2) cmd_install ;;
    3) cmd_update ;;
    4) cmd_backup ;;
    5) cmd_restore ;;
    6) cmd_status ;;
    0 | '') say MENU_BYE ;;
    *)
      say_err MENU_INVALID
      return 2
      ;;
  esac
}

main() {
  load_language
  local command="${1:-}"
  case "$command" in
    '') cmd_menu ;;
    doctor | install | update | backup | restore | status)
      shift
      "cmd_$command" "$@"
      ;;
    -h | --help | help) say USAGE ;;
    *)
      say_err UNKNOWN_COMMAND "$command"
      say_err USAGE
      return 2
      ;;
  esac
}

main "$@"
