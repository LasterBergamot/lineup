---
paths:
  - "selfhost/**"
  - "scripts/selfhost_e2e.py"
---

# Self-hosted stack (`selfhost/`)

The optional second way to run Lineup: one always-on machine, reachable only through a Cloudflare Tunnel, with its own Postgres and its own Supabase Auth (Google sign-in only). The cloud install (Fly, Pages, Supabase) is a separate deployment with separate data and is not touched by anything here. The working plan is `self-host-plan.md`; this file is the reference for what exists. **Privacy of the deployment is a hard rule**: the repo is public, so nothing here says who hosts it, where, or its real domain. Examples use `lineup.example.com`.

## What is in `selfhost/` (#255)

- `compose.yml` (project name `lineup`): `db` (postgres:17), `migrate` (one shot: `python -m lineup.db.selfhost_bootstrap`), `auth` (`supabase/gotrue`), `api`, `web` (Caddy plus the built app, port 8080) and `cloudflared` (behind the `tunnel` profile). Images are `image:@sha256:` pinned for third parties and `ghcr.io/lasterbergamot/lineup-{api,web}:${LINEUP_VERSION}` for ours (published by T5; until then only the test overlay builds them). **Nothing publishes a port**: the tunnel is the only way in, which is what makes `CLIENT_IP_HEADER=Cf-Connecting-IP` safe. Every service has `cap_drop: [ALL]` and `no-new-privileges`. Two services add capabilities back: `db` (the official image starts as root, then drops to `postgres`) and `web` (`NET_BIND_SERVICE`: the Caddy binary carries that file capability, and the kernel refuses to exec it ("operation not permitted") when the container's capability set lacks it, although port 8080 needs no privilege).
- Networks: `internal` is `internal: true` (no internet route; `db`, `migrate`, `api` live there only), `egress` is for `auth` (it calls Google), `edge` joins `web` and `cloudflared`. `api` sits on `internal` only and gets only the `lineup_app` password. `migrate` and `db` hold the superuser password. `api` is `ENV=production` with `DATABASE_TLS=internal-network` (plain Postgres on the private network: T2) and `AUTH_JWKS_URL=http://auth:9999/...` so it never goes out through the tunnel to fetch keys.
- `postgres-init/01-databases.sh` (mode 755; runs only on an empty data volume): creates databases `lineup` and `auth` and the `supabase_auth_admin` role. It does **not** create `lineup_app`: the Alembic migration does, and `selfhost_bootstrap` sets its password.
- `.env.example`: every variable the compose file needs, with fake values and `example.com` only. The real `selfhost/.env` is written by `lineup.sh install` (T6), is git-ignored and denied to Claude (`.claude/settings.json`). **Never read, print or commit it.** `AUTH_JWT_KEYS` is JSON and must be single-quoted. Passwords must be URL-safe (two sit inside connection URLs). Fresh key: `python -m lineup.auth.signing_key` from `backend/`.
- `compose.test.yml`: the test overlay, not shipped. Builds `migrate`, `api` and `web` from the checked-out code, publishes `web` on `127.0.0.1:8088:8080` (the only published port there is) and enables password sign-in so the test gets real tokens without Google.
- `GOTRUE_JWT_DEFAULT_GROUP_NAME` is **not** set: GoTrue logs "not supported by Supabase's GoTrue, will be removed soon" for it, and tokens still carry `aud=authenticated`, which is all the API checks. (A second warning, about `GOTRUE_JWT_ADMIN_GROUP_NAME`, comes from GoTrue's own default and cannot be silenced.)

## The end-to-end test: `task selfhost:test`

`scripts/selfhost_e2e.py` (stdlib only; run with the backend's Python from `backend/`, which the task does) writes a throw-away `.env` with generated secrets into a private temp directory, starts `compose.yml` + `compose.test.yml` as project `lineup-selfhost-test` (`up -d --build --wait`), and then:

1. signs two users up against the stack's **own Auth**, from inside the `api` container over the private network (`docker compose exec -T api python -c ...`, credentials on stdin). It cannot use `POST /auth/v1/signup` through `web`: the Caddy allow-list deliberately has no `signup` (Google-only install), and the test asserts that path is 404. Sign-up carries `data.full_name` because the smoke test expects the inviter's name in the token;
2. **reuses `scripts/smoke_live.py`** against `http://localhost:8088/api` (the single definition of the API steps; never re-type them here);
3. asserts `/auth/v1/admin/users` and `/auth/v1/signup` are 404, `/api/docs` is 404, `/join/x` returns the app, the JWKS is public, `POST /api/lineups` with a token returns a real `application/pdf` (`%PDF`), the same call without a token is 401 and with a token signed by a different key (same `kid` and claims, forged inside the container) is 401;
4. checks `docker compose ps` publishes only `web` on `127.0.0.1:8088`;
5. always runs `down -v --remove-orphans` and deletes the temp directory. Tokens and passwords are never printed (failures print the check's name, or an exception class).

Compose v5 (and the plan's minimum, 2.20) accept `up --wait` with a one-shot `migrate` that exits 0; if an older Compose does not, switch to `up -d` plus polling and keep `migrate`'s `depends_on` condition. Tests for its helpers: `backend/tests/test_selfhost_e2e_script.py`.

## Guards

`backend/tests/test_selfhost_config.py` reads `selfhost/compose.yml` as text (PyYAML is not a direct dependency) and fails on: a published port or `build:`, a third-party image without a digest, a service without `cap_drop: [ALL]` or `no-new-privileges`, `api` off the `internal`-only network, a missing `internal: true`, `ENV` other than `production`, a secret-looking variable that is not a `${...}` reference, a literal password in a URL, capabilities added beyond the documented ones; for `.env.example`: any host that is not `example.com`, any 41+ character secret-looking string; for the whole `selfhost/` tree (except `.env` and `backups/`, which it never reads) and `self-host-plan.md`: any `*.pages.dev`, `*.fly.dev` or `*.supabase.co` address. When you change the compose file on purpose, change the matching expectation in the same PR; never loosen a check to make a test pass.

## Updating pinned images

Dependabot has a `docker-compose` entry for `/selfhost` (minor and patch grouped). Look a digest up with `docker buildx imagetools inspect <image>:<tag>` (the multi-arch index digest) and never invent one. The Auth version and the four token tables that backups exclude (`sessions`, `refresh_tokens`, `one_time_tokens`, `flow_state`) come from the T1 spike (#252); re-check the tables when bumping Auth.

## CI

The `Self-hosted stack (report only)` job in `ci.yml` (`selfhost`, `continue-on-error: true`, no path filter) runs `task selfhost:test`. It does not block a PR until the owner makes it a required check once it has proven stable.
