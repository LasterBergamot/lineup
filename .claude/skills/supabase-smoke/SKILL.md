---
name: supabase-smoke
description: Run the live smoke test against the dev Supabase project — start the API on the transaction pooler, create a team, player and saved lineup, generate a DOCX from it, create/preview/accept/revoke an invite link as a second user, then delete everything it created. Use after touching backend/lineup/db/models.py, backend/lineup/db/engine.py, Alembic migrations or Postgres connection settings, since SQLite-only tests can't catch Postgres/pooler bugs.
model: haiku
---

`.claude/rules/backend-db.md` asks for this after any model or engine change. SQLite tolerated two bugs that
broke on Supabase: aware datetimes rejected by asyncpg, and `DuplicatePreparedStatementError`
behind the pooler. This runs the real path end to end.

CI runs the same script after every successful dev deploy (job `smoke` in `deploy-dev.yml`), so a
manual run is mainly for checking a change *before* it is merged.

**It writes to the shared dev database.** Rows are created and then deleted. Tell the user
before you start and get a go-ahead. Never run this against a prod project.

**Never read `backend/.env`.** It's denied in `.claude/settings.json`. Let `task` source it, and never
echo `DATABASE_URL`.

## 1. Preconditions

```bash
task db:status                      # must say "postgres (Supabase pooler: …)"
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health   # is something already on :8000?
```

- If `db:status` reports SQLite, ask before running `task db:postgres`, since it edits
  `backend/.env`. Remember to switch back in step 5.
- If port 8000 is taken (usually the `lineup` container from `task up`), ask before running
  `task down`.
- The dev schema must be at Alembic head. If the change added a migration, the user must
  have applied it already with `task migrate:supabase` (owner credentials from
  `backend/.env.migrate`), never through the pooler.
- The app should connect as the least-privilege `lineup_app` role (`task db:create-app-role`
  rewrites the pooler URL in `backend/.env`; it asks for a typed `yes` first because it rotates
  the password and breaks the Fly and keepalive secrets until they are updated). Running this smoke test as `lineup_app` is the
  acceptance check for #68: it proves RLS plus the grants let the API do everything it needs. A
  `permission denied` or `row-level security` error here means a new table is missing its
  policy or grants in its migration.

## 2. Start a fake Supabase Auth, then the API

Every data route needs a signed-in user, and this test only wants the *database* path, so it
does not sign in with Google. `scripts/smoke_auth.py` is a throw-away stand-in: it serves its
own public key set on localhost and writes a token for a fixed smoke user to a file. Nothing touches
the real Supabase Auth.

```bash
uv run --project backend python scripts/smoke_auth.py --port 54399 \
  --token-file /tmp/smoke.jwt --second-token-file /tmp/smoke2.jwt &
```

The second token belongs to a different (fixed) user. The invitation step needs it, because the
team's creator is already a member and accepting your own link proves nothing.

Then start the API **in the background** with `SUPABASE_URL` pointing at it. This sources
`backend/.env` (DB settings) first and overrides only `SUPABASE_URL` for this one process, so
it works even if `.env` already sets the real project URL:

```bash
cd backend && set -a && . ./.env && set +a && SUPABASE_URL=http://127.0.0.1:54399 uv run uvicorn app:app
```

Wait until `/health` answers 200 (`/docs` is off under `ENV=production`, which the Supabase `.env` sets; startup also fails closed unless `DATABASE_URL` has `ssl=` and `SUPABASE_URL` is set). The local server has no LibreOffice, so it renders DOCX only.

## 3. Run the smoke script

The steps live in one committed script, `scripts/smoke_live.py`, which CI also runs after every
dev deploy (`.github/workflows/deploy-dev.yml`, job `smoke`, #190). Do not re-type them as curl
commands here: change the script and its test (`backend/tests/test_smoke_live.py`) instead.

```bash
python3 scripts/smoke_live.py --base-url http://127.0.0.1:8000 \
  --token-file /tmp/smoke.jwt --second-token-file /tmp/smoke2.jwt
```

It needs no `jq`. It marks every row `smoke-<unix time>`, and it:

- checks that an anonymous request gets 401;
- creates a team, a player and a saved lineup, reads the lineup back (frozen names), generates a DOCX
  (200, a wordprocessingml type, `Cache-Control: no-store`) and searches the opponent pool;
- runs the invitation path (migration `b7d2e9a41c53` added `invited_by_name`, and this proves it works
  on Postgres): create a link, preview it without a token (team name and inviter `Smoke Owner`), a
  non-member cannot create one (404), the second user joins as `member` (twice, idempotent), the
  member list has two rows, the member's own attempt is 403, the list never exposes a code, revoking
  returns 204 and a revoked link answers 410;
- **always cleans up**, even after a failed step: removes the joined member, then the lineup, the
  player and the team (a team with a lineup or player in it answers 409), and finally sweeps teams
  marked `smoke-<time>` that are more than an hour old (left by a crashed run; this works because
  `smoke_auth.py` signs the same two users every time).

Each step prints `ok` or `FAIL` with the status code; the exit code is 0 only if everything passed.
Neither the tokens nor the invite code are printed. An invite step failing with
`column ... invited_by_name does not exist` means the migration is not on dev.

## 4. Clean up the files

The script deletes its database rows itself. Remove the token files:

```bash
rm -f /tmp/smoke.jwt /tmp/smoke2.jwt
```

If the script itself could not run (for example the API never started), nothing was written.

## 5. Restore and report

- Stop the background API and the `smoke_auth.py` process.
- Run `task db:sqlite` if you switched in step 1, and `task up` if you stopped the
  container.
- Report the script's output (each step's status code). On any 500, include the relevant uvicorn traceback lines
  (no URLs or secrets). Typical causes:
  - `DuplicatePreparedStatementError`: the pooler connect args in `backend/lineup/db/engine.py`
  - "can't subtract offset-naive and offset-aware datetimes" / `DataError` on timestamps:
    the model datetime defaults
  - missing column/table: the dev schema isn't at head
  - `401` everywhere: the API was started without `SUPABASE_URL=http://127.0.0.1:54399`, or `smoke_auth.py` isn't running
  - a `503 Authentication unavailable`: the fake key server isn't reachable on that port
