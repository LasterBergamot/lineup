# Roadmap: Backend

Status: core persistence (Teams/Players/SavedLineups on the target snapshot schema) is
**done**, the app can already run against a **dev** Supabase Postgres project, requests are
authenticated with Supabase JWTs and the team-membership tables exist (see
[[Current State: Backend]]). Using membership for access, invitations, team-scoped RLS and the
production Supabase project are **not done yet**. (The current-state design — ERD, snapshot
strategy — lives in [[Current State: Backend]]; this page only covers what is still ahead.)

## Team collaboration: what is done and what is next

The tables exist (`team_members`, `team_invitations`, see the ERD in [[Current State: Backend]]),
creating a team adds its creator as an `owner` member, and the owner columns are `NOT NULL`.
Nothing *reads* membership yet: access is still "rows you created". Still ahead, in order:

1. **Team-scoped access** (#49, #48, #50): a team becomes the workspace. `players.team_id` and a new
   `saved_lineups.team_id` become required, and the rule everywhere is "the caller is a member of the
   row's team". `user_id` turns into an audit-only `created_by`.
2. **Invitation endpoints** (#51): multi-use links that expire (24 h by default), can be revoked and
   are stored only as a SHA-256 hash; members list; leave / transfer ownership.
3. **Replace the interim RLS policy** (#21) with team-scoped ones using the same membership rule.

## Supabase & OAuth integration

1. **Authentication**
   - *Code done:* `get_current_user_id()` (`backend/lineup/auth/dependencies.py`) validates the
     Bearer JWT against the project's JWKS and returns `sub`; every repository filters on the
     required user id (see [[Current State: Backend]]).
   - *Still manual (one-off, per project):* create the Google OAuth client and enable the Google
     provider in the Supabase dashboard — step by step in [[Auth Setup]].
2. **Production database cutover** *(remaining piece — the dev half is done)*
   - Done for dev: `asyncpg` is a dependency, the engine is dialect-aware, and the app runs
     against the `lineup-dev` Supabase project via `DATABASE_URL` (see
     [[Current State: Backend]]).
   - Still to do: create a separate `lineup-prod` Supabase project, run `alembic upgrade head`
     against it, and wire its `DATABASE_URL` + secrets into the deployment (paired with CD).

   This dev cutover is independent of the auth/RLS sequence below: the dev database can be
   used before any of steps 1, 3–5 exist.
3. **Row Level Security (RLS) in PostgreSQL**
   - *Done:* RLS is on for every table (deny by default), the `lineup_app` role exists and the
     API runs as it, with an interim allow-all policy (see [[Current State: Backend]]). The
     policies below replace that interim one.
   - `teams`: public read for `is_public = true` (powers the opponent pool); read/write
     restricted to `owner_id = auth.uid()` or team members.
   - `players` & `saved_lineups`: restricted to team members / creator
     (`auth.uid() = user_id`).
4. **Onboarding hook**
   - On first login, check if the user has an existing team or pending invitation.
   - If not, prompt for a team name → `POST /teams` → `owner_id = user_id`. This becomes
     the user's default team. (UI side of this is [[Roadmap: Frontend]].)
5. **Team invitations**
   - `POST /teams/{id}/invitations` — generate an invite code/link.
   - `POST /teams/join?invite_code=...` — adds the accepting user to `team_members`.

## Rollout sequencing

```mermaid
flowchart TD
    A[Done: get_current_user_id validates the Supabase JWT] --> B[Done: team_members / team_invitations tables + migration]
    B --> C[Team-scoped access instead of creator-only]
    C --> D[Enable RLS policies in Postgres]
    D --> E[Cut DATABASE_URL to Supabase Postgres in prod<br/>dev project already cut over]
    E --> F[Ship invitation endpoints]
```

The order matters: the JWT check landed first, on its own, because it is small and reversible,
and team membership builds on a real user id. It is deliberately sequenced before the
Postgres/RLS cutover (steps D–E) so auth can be validated against SQLite first.
