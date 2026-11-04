#!/bin/bash
# Nightly backup of the self-hosted install. Runs inside the `backup` service (postgres:17 image),
# which reaches the database through the standard PG* environment variables.
#
#   backup.sh                  run forever: one backup every day at BACKUP_HOUR (UTC, default 3)
#   backup.sh --once           run one backup now and exit (what `lineup.sh backup` and `update` use)
#   backup.sh --once --safety  the same, under a time-stamped name so it never replaces a daily
#                              backup (used by `lineup.sh restore` before it overwrites anything)
#
# A backup is two files in /backups: `lineup-<id>.dump` and `auth-<id>.dump`, where <id> is the UTC
# date (or `safety-<timestamp>`). Both are written under a `.tmp` name first and renamed only when
# BOTH succeeded, so a half backup never looks like a good one. The `auth` dump leaves out the data
# of the four token tables (sessions, refresh tokens, one-time tokens, flow state): a stolen backup
# then cannot be used to take over a signed-in session, and a restore simply signs everyone out.
# A fifth table, mfa_amr_claims, is left out too although it holds no secret: every row points at a
# session, so with the sessions gone a restore fails on its foreign key (found by the end-to-end
# test). Re-check this list, and the foreign keys into these tables, when Auth is upgraded.
#
# On success `last-success` holds the time (seconds since 1970); `lineup.sh status` reads it. Files
# older than BACKUP_RETENTION_DAYS (default 30) are deleted after a successful backup. A failure logs
# the fact and the exit code only: pg_dump's own message can quote SQL, so it is discarded. Older
# backups are never touched by a failed run.
set -euo pipefail

# BACKUPS_DIR is for the automated tests; in the container the folder is always /backups.
BACKUPS="${BACKUPS_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
HOUR="${BACKUP_HOUR:-3}"

log() {
  printf '%s backup: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

# Dump one database to "$BACKUPS/<name>-<id>.dump.tmp". Extra arguments go to pg_dump.
dump_database() {
  local name="$1" id="$2"
  shift 2
  pg_dump -Fc --dbname "$name" --file "$BACKUPS/$name-$id.dump.tmp" "$@" 2>/dev/null
}

# One complete backup under the id given as $1. Returns non-zero (after cleaning up) on failure.
run_backup() {
  local id="$1" code=0
  rm -f "$BACKUPS"/*.dump.tmp
  dump_database lineup "$id" || code=$?
  if [ "$code" -eq 0 ]; then
    dump_database auth "$id" \
      --exclude-table-data=auth.sessions \
      --exclude-table-data=auth.refresh_tokens \
      --exclude-table-data=auth.one_time_tokens \
      --exclude-table-data=auth.flow_state \
      --exclude-table-data=auth.mfa_amr_claims || code=$?
  fi
  if [ "$code" -ne 0 ]; then
    rm -f "$BACKUPS"/*.dump.tmp
    log "FAILED (pg_dump exit code $code); the older backups are untouched"
    return 1
  fi
  mv "$BACKUPS/lineup-$id.dump.tmp" "$BACKUPS/lineup-$id.dump"
  mv "$BACKUPS/auth-$id.dump.tmp" "$BACKUPS/auth-$id.dump"
  date -u +%s >"$BACKUPS/last-success.tmp"
  mv "$BACKUPS/last-success.tmp" "$BACKUPS/last-success"
  log "ok: $id"
  find "$BACKUPS" -maxdepth 1 -name '*.dump' -mtime +"$RETENTION_DAYS" -delete
}

# Seconds from now until the next BACKUP_HOUR:00 UTC.
seconds_until_next_run() {
  local now target
  now="$(date -u +%s)"
  target="$(date -u -d "$(date -u +%F) $(printf '%02d' "$((10#$HOUR))"):00:00" +%s)"
  if [ "$target" -le "$now" ]; then
    target=$((target + 86400))
  fi
  echo $((target - now))
}

main() {
  local once=0 safety=0 argument
  SLEEPER=""
  for argument in "$@"; do
    case "$argument" in
      --once) once=1 ;;
      --safety) safety=1 ;;
      *)
        log "unknown argument: $argument"
        return 2
        ;;
    esac
  done
  case "$HOUR" in
    '' | *[!0-9]* | ???*)
      log "BACKUP_HOUR must be a number from 0 to 23"
      return 2
      ;;
  esac
  if [ "$((10#$HOUR))" -gt 23 ]; then
    log "BACKUP_HOUR must be a number from 0 to 23"
    return 2
  fi
  umask 077

  if [ "$once" -eq 1 ]; then
    if [ "$safety" -eq 1 ]; then
      run_backup "safety-$(date -u +%Y%m%dT%H%M%SZ)"
    else
      run_backup "$(date -u +%F)"
    fi
    return
  fi

  # `sleep` runs in the background and is waited for, so that a stop signal ends the loop at once
  # instead of after the sleep (this script is the container's first process).
  trap 'kill "$SLEEPER" 2>/dev/null || true; exit 0' TERM INT
  log "started; one backup every day at $(printf '%02d' "$((10#$HOUR))"):00 UTC, kept $RETENTION_DAYS days"
  while true; do
    sleep "$(seconds_until_next_run)" &
    SLEEPER=$!
    wait "$SLEEPER"
    run_backup "$(date -u +%F)" || true
  done
}

main "$@"
