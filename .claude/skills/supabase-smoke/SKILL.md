---
name: supabase-smoke
description: Run the live smoke test against the dev Supabase project — start the API on the transaction pooler, create a team, player and saved lineup, generate a DOCX from it, create/preview/accept/revoke an invite link as a second user, then delete everything it created. Use after touching backend/lineup/db/models.py, backend/lineup/db/engine.py, Alembic migrations or Postgres connection settings, since SQLite-only tests can't catch Postgres/pooler bugs.
model: haiku
---

`.claude/rules/backend-db.md` asks for this after any model or engine change. SQLite tolerated two bugs that
broke on Supabase: aware datetimes rejected by asyncpg, and `DuplicatePreparedStatementError`
behind the pooler. This runs the real path end to end.

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
own public key set on localhost and writes a token for a random user to a file. Nothing touches
the real Supabase Auth.

```bash
uv run --project backend python scripts/smoke_auth.py --port 54399 \
  --token-file /tmp/smoke.jwt --second-token-file /tmp/smoke2.jwt &
```

The second token belongs to a different random user. The invitation step needs it, because the
team's creator is already a member and accepting your own link proves nothing.

Then start the API **in the background** with `SUPABASE_URL` pointing at it. This sources
`backend/.env` (DB settings) first and overrides only `SUPABASE_URL` for this one process, so
it works even if `.env` already sets the real project URL:

```bash
cd backend && set -a && . ./.env && set +a && SUPABASE_URL=http://127.0.0.1:54399 uv run uvicorn app:app
```

Wait until `/health` answers 200 (`/docs` is off under `ENV=production`, which the Supabase `.env` sets; startup also fails closed unless `DATABASE_URL` has `ssl=` and `SUPABASE_URL` is set). The local server has no LibreOffice, so it renders DOCX only.

## 3. Exercise the API

Use a unique marker so the rows are easy to find and clean up. This needs `jq`.

```bash
M="smoke-$(date +%s)"; B=http://127.0.0.1:8000; A="authorization: Bearer $(cat /tmp/smoke.jwt)"
TEAM=$(curl -sf -X POST $B/teams -H "$A" -H 'content-type: application/json' -d "{\"name\":\"$M team\"}" | jq -r .id)
PLAYER=$(curl -sf -X POST $B/players -H "$A" -H 'content-type: application/json' \
  -d "{\"name\":\"$M player\",\"nssz_number\":\"SMOKE1\",\"team_id\":\"$TEAM\"}" | jq -r .id)
LINEUP=$(curl -sf -X POST $B/lineups/saved -H "$A" -H 'content-type: application/json' -d "{
  \"team_id\":\"$TEAM\",\"source_team_id\":\"$TEAM\",\"opponent_name\":\"$M opponent\",\"division\":\"OB II.\",
  \"cap\":\"Fehér\",\"date\":\"2026. 01. 01.\",\"coach\":\"Smoke Coach\",
  \"players\":[{\"source_player_id\":\"$PLAYER\",\"cap_number\":1}]}" | jq -r .id)
curl -sf -H "$A" "$B/lineups/saved/$LINEUP" | jq '{team_name, players: [.players[].name]}'
curl -sf -H "$A" -o /tmp/$M.docx -w 'generate: %{http_code} %{content_type}\n' -X POST "$B/lineups/saved/$LINEUP/generate?format=docx"
curl -sf -H "$A" "$B/teams/pool?search=$M" | jq length
```

Then the invitation path (migration `b7d2e9a41c53` added `invited_by_name`, and this is what
proves it works on Postgres). Both tokens carry the name `Smoke Owner`:

```bash
A2="authorization: Bearer $(cat /tmp/smoke2.jwt)"
INV=$(curl -sf -X POST $B/teams/$TEAM/invitations -H "$A" -H 'content-type: application/json' -d '{"expires_in_hours":2}')
CODE=$(echo "$INV" | jq -r .code); INV_ID=$(echo "$INV" | jq -r .id)
curl -sf $B/invitations/$CODE | jq '{team_name, invited_by_name}'                    # no token: public preview
curl -s -H "$A2" -o /dev/null -w 'non-owner create %{http_code}\n' -X POST $B/teams/$TEAM/invitations   # 404 (not a member yet)
curl -sf -H "$A2" -X POST $B/invitations/$CODE/accept | jq '{name, role}'            # role member
curl -sf -H "$A2" -X POST $B/invitations/$CODE/accept | jq -r .role                  # repeat: still member
curl -sf -H "$A" $B/teams/$TEAM/members | jq 'map({role, is_you})'                   # owner + member
curl -s -H "$A2" -o /dev/null -w 'member create %{http_code}\n' -X POST $B/teams/$TEAM/invitations    # 403
curl -sf -H "$A" $B/teams/$TEAM/invitations | jq length                              # 1, and no "code" field
curl -s -H "$A" -o /dev/null -w 'revoke %{http_code}\n' -X DELETE $B/teams/$TEAM/invitations/$INV_ID   # 204
curl -s -o /dev/null -w 'preview revoked %{http_code}\n' $B/invitations/$CODE      # 410
MEMBER=$(curl -sf -H "$A" $B/teams/$TEAM/members | jq -r '.[] | select(.is_you|not) | .user_id')
```

Check: each create returns an id (a `null` means it failed, so read the uvicorn output),
the GET shows the frozen names, and generate returns 200 with a wordprocessingml type. For the
invitation block: the preview shows the team name and `Smoke Owner`, the second user joins as
`member` (twice, idempotent), the member list has two rows, the member's own invite attempt is
403, the list never exposes a code, and a revoked link answers 410. An invite step failing with
`column ... invited_by_name does not exist` means the migration is not on dev.

## 4. Clean up (always, even if step 3 failed)

Remove the joined member (its `DELETE /teams/{id}/members/{user_id}` is owner-only), then delete
the lineup, then the player, then the team, because the team delete returns
409 while a saved lineup or a player is still in it:

```bash
curl -s -H "$A" -o /dev/null -w 'del member %{http_code}\n' -X DELETE "$B/teams/$TEAM/members/$MEMBER"   # 204
curl -s -H "$A" -o /dev/null -w 'del lineup %{http_code}\n' -X DELETE "$B/lineups/saved/$LINEUP"   # 204
curl -s -H "$A" -o /dev/null -w 'del player %{http_code}\n' -X DELETE "$B/players/$PLAYER"          # 204
curl -s -H "$A" -o /dev/null -w 'del team %{http_code}\n'   -X DELETE "$B/teams/$TEAM"              # 200
curl -sf -H "$A" "$B/teams/pool?search=$M" | jq length                                        # 0
rm -f /tmp/$M.docx /tmp/smoke.jwt /tmp/smoke2.jwt
```

If an id is missing because a create failed partway, list and delete by the marker
instead: `GET /teams?limit=200` and `GET /players?limit=200` (add `-H "$A"`), filtered on `$M` with `jq` (`limit` is capped at 200, so page with `&offset=` if there are more).

## 5. Restore and report

- Stop the background API and the `smoke_auth.py` process.
- Run `task db:sqlite` if you switched in step 1, and `task up` if you stopped the
  container.
- Report each step's status code. On any 500, include the relevant uvicorn traceback lines
  (no URLs or secrets). Typical causes:
  - `DuplicatePreparedStatementError`: the pooler connect args in `backend/lineup/db/engine.py`
  - "can't subtract offset-naive and offset-aware datetimes" / `DataError` on timestamps:
    the model datetime defaults
  - missing column/table: the dev schema isn't at head
  - `401` everywhere: the API was started without `SUPABASE_URL=http://127.0.0.1:54399`, or `smoke_auth.py` isn't running
  - a `503 Authentication unavailable`: the fake key server isn't reachable on that port
