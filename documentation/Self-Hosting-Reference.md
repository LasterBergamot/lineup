# Self-Hosting Reference

The technical reference for the optional self-hosted install (`selfhost/`): how it is built, why, what every
service and setting does, how updates, backups and restores work, and how CI tests it. For the step-by-step
operator instructions read [[Self Hosting Guide]] (English) or [[Saját gépes telepítés]] (Hungarian). The
working plan is `self-host-plan.md` in the repo root (epic #250) while it exists; the rules for working in
`selfhost/` are in `.claude/rules/selfhost.md`.

**Privacy of the deployment.** This repo and wiki are public. Nothing here says who runs a self-hosted install,
where, or on which domain; examples use `lineup.example.com`.

Contents:

1. [What it is and how it differs from the cloud install](#1-what-it-is-and-how-it-differs-from-the-cloud-install)
2. [Architecture](#2-architecture)
3. [Services](#3-services)
4. [Settings](#4-settings)
5. [Network layout](#5-network-layout)
6. [Tooling: `lineup.sh`, `task deploy`, releases](#6-tooling)
7. [Updates and migrations](#7-updates-and-migrations)
8. [Backups and restore](#8-backups-and-restore)
9. [Limits and gotchas](#9-limits-and-gotchas)
10. [How CI tests it](#10-how-ci-tests-it)
11. [Not yet implemented in this repo](#11-not-yet-implemented-in-this-repo)

---

## 1. What it is and how it differs from the cloud install

A second, separate way to run Lineup on **one always-on machine** (a NAS or small server), reachable from the
internet through a Cloudflare Tunnel, with no Fly.io, Cloudflare Pages or Supabase project. Both installs can
exist at the same time; they share no data. Nothing in the cloud setup (`compose.yml`, `compose.e2e.yml`,
`backend/fly.toml`, the deploy workflow) is changed by the self-hosted one, and every behaviour added to shared
code is opt-in through a new environment variable, so with the variable unset the cloud install behaves exactly
as before.

| | Cloud install | Self-hosted install |
|---|---|---|
| API | Fly.io, scales to zero | `api` container on the machine, always on |
| Web app | Cloudflare Pages (`VITE_API_URL`, `VITE_SUPABASE_URL`) | `web` container: Caddy plus the built app, same origin as API and Auth |
| Database and sign-in | Supabase (hosted Postgres and Auth) | Postgres 17 container and the open-source Supabase Auth server (`supabase/gotrue`) |
| Sign-in methods | Google | Google only, no passwords, no e-mail server |
| Who may sign in | Supabase project's Google test-user list | The self-hosted Google Cloud project's test-user list |
| Reaching it | Public Fly and Pages hosts | Cloudflare Tunnel; the machine publishes no port |
| Deploy | Push to `develop` runs the deploy workflow; `task deploy -- --cloud` for a manual run | The machine **pulls** released images when a person runs `./lineup.sh update`; no self-hosted runner, nothing connects in |
| Backups | The provider's | Nightly dump to a folder on the same machine, unencrypted, 30 days |
| GDPR | See [[Privacy and Security]] | The same rules apply; see its section on self-hosted installs |

---

## 2. Architecture

```
Browser ──> Cloudflare ──> cloudflared ──> web (Caddy + built app, :8080)
                                            ├─ /api/*     ──> api (FastAPI + LibreOffice, :8000)
                                            └─ /auth/v1/* ──> auth (Supabase Auth, :9999), allow-listed paths only
                                      db (postgres:17): databases `lineup`, `auth`
                                      migrate (one-shot) · backup (nightly, writes to the backup folder)
```

Why it is shaped this way:

- **No published ports.** Traffic can only arrive through the tunnel, which is what makes
  `CLIENT_IP_HEADER=Cf-Connecting-IP` safe: nobody can reach the API without passing Cloudflare, so the header
  cannot be forged.
- **One origin.** App, API and Auth share one domain, so CORS stays unset, and the frontend's existing fallback to
  `/api` works as it is. The web image is built with `VITE_AUTH_SAME_ORIGIN=true`, which makes sign-in use the
  page's own origin.
- **Generic images.** The web image has no domain built in, so images can be public without revealing where they run.
- **Least privilege.** `api` gets only the `lineup_app` password and sits on an internal network with no internet
  route. `migrate` is the only service with the database superuser password besides `db` and `backup`. `auth` has its
  own role and database.
- **Allow-listed Auth paths.** Caddy proxies only the Auth paths the browser needs (`authorize`, `callback`, `token`,
  `logout`, `user`, `settings`, `.well-known/jwks.json`). Everything else under `/auth/v1/`, above all `/admin`,
  answers 404 from outside. There is no `signup`: it is a Google-only install.
- **No access logs.** The Caddyfile has no `log` directive on purpose: invite codes are URL path segments and must
  not reach any log. Auth logs at `warn`, and Docker rotates container logs at 10 MB times 3 files.

---

## 3. Services

All in `selfhost/compose.yml` (project name `lineup`). Third-party images are pinned by digest; ours are
`ghcr.io/lasterbergamot/lineup-{api,web}:${LINEUP_VERSION}`. Every service drops all capabilities and sets
`no-new-privileges`; `db` and `web` add back the few capabilities the images need (see `.claude/rules/selfhost.md`).

| Service | Image | Role | Networks |
|---|---|---|---|
| `db` | `postgres:17` | One server, two databases: `lineup` (the app) and `auth` (Supabase Auth). A script in `postgres-init/` creates them and the `supabase_auth_admin` role on an empty volume. Data in the named volume `lineup-db` | `internal` |
| `migrate` | the API image | One shot, runs `python -m lineup.db.selfhost_bootstrap`: Alembic upgrade to head as the superuser, then sets the password of the `lineup_app` role the migration creates. Idempotent, runs on every start and update | `internal` |
| `auth` | `supabase/gotrue` | Sign-in with Google only. Signs tokens with an ES256 key from `AUTH_JWT_KEYS`; publishes the public key at `.well-known/jwks.json` | `internal`, `egress` (it calls Google) |
| `api` | the API image | FastAPI with `ENV=production`. Verifies tokens against the issuer `PUBLIC_URL/auth/v1` but fetches the keys from `http://auth:9999` (`AUTH_JWKS_URL`), so it never leaves through the tunnel | `internal` |
| `web` | the web image | Caddy: serves the built app (deep links fall back to `index.html`), proxies `/api/*` to `api` and the allow-listed Auth paths to `auth`, sets the security headers (a test keeps them identical to `frontend/public/_headers`) | `internal`, `edge` |
| `cloudflared` | `cloudflare/cloudflared` | Runs the tunnel. Behind the Compose profile `tunnel` so tests run without a token; a real install sets `COMPOSE_PROFILES=tunnel` | `edge` |
| `backup` | `postgres:17` | Nightly dump to the backup folder (see [section 8](#8-backups-and-restore)). Added by the installer work, see [section 11](#11-not-yet-implemented-in-this-repo) | `internal` |

---

## 4. Settings

`selfhost/.env` is written by `lineup.sh install` (mode 600, git-ignored, denied to Claude in
`.claude/settings.json`). `selfhost/.env.example` documents every variable with fake values. Never read, print or
commit the real file.

| Variable | Used by | Meaning |
|---|---|---|
| `LINEUP_VERSION` | all our images | Release tag to run, such as `v0.2.0`. `update` changes this line |
| `PUBLIC_URL` | `auth`, `api` | Public address, `https://`, no trailing slash. It is the token issuer (`PUBLIC_URL/auth/v1`), the Auth site URL and redirect base, and the base of invitation links (`APP_BASE_URL`) |
| `COMPOSE_PROFILES` | Compose | `tunnel` in a real install; unset in tests |
| `TUNNEL_TOKEN` | `cloudflared` | The tunnel token from the Cloudflare dashboard (the token only, not the command) |
| `POSTGRES_PASSWORD` | `db`, `migrate`, `backup` | Database superuser |
| `AUTH_DB_PASSWORD` | `db` (init), `auth` | Password of `supabase_auth_admin` |
| `LINEUP_APP_PASSWORD` | `migrate`, `api` | Password of the least-privilege `lineup_app` role |
| `AUTH_JWT_SECRET` | `auth` | Required by Auth, unused for tokens (they use the ES256 key). Alphanumeric on purpose |
| `AUTH_JWT_KEYS` | `auth` | JSON array printed by `python -m lineup.auth.signing_key`; one line, in **single quotes** in `.env` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_SECRET` | `auth` | The Google sign-in client of the self-hosted Google Cloud project |
| `AUTH_EMAIL_ENABLED` | `auth` | `false` in a real install. The CI stack sets `true` so it can get real tokens without Google |
| `BACKUP_DIR` | `backup` | Backup folder; default `./backups` |
| `BACKUP_HOUR` | `backup` | UTC hour of the nightly backup; default 3 |
| `LINEUP_LANG` | `lineup.sh` | Language of the installer's messages (`hu` default, or `en`) |

Fixed values the compose file gives the `api` service (see [[Current State: Everything Else]] for what each setting
does): `ENV=production`, `DATABASE_URL` for `lineup_app` on host `db`, `DATABASE_TLS=internal-network`
(plaintext Postgres is accepted only on the private network and only for a single-label host such as `db`, never
`localhost` or a dotted name), `SUPABASE_URL=${PUBLIC_URL}`, `AUTH_JWKS_URL=http://auth:9999/.well-known/jwks.json`,
`APP_BASE_URL`, `CLIENT_IP_HEADER=Cf-Connecting-IP`, `PDF_MAX_CONCURRENT=1`.

Passwords must be URL-safe (letters and digits): two of them sit inside connection URLs.

---

## 5. Network layout

| Network | Properties | Members |
|---|---|---|
| `internal` | `internal: true`: **no route to the internet** | `db`, `migrate`, `auth`, `api`, `web`, `backup` |
| `egress` | Normal bridge, outbound allowed | `auth` only (it calls Google to exchange the sign-in code) |
| `edge` | Normal bridge | `web`, `cloudflared` |

So `db` and `api` cannot call out, `cloudflared` can only reach `web`, and nothing publishes a host port. A guard
test (`backend/tests/test_selfhost_config.py`) fails on a published port, a `build:`, an unpinned image, a service
without `cap_drop`, or `api` on any network other than `internal`.

---

## 6. Tooling

| Tool | Where it runs | What it does |
|---|---|---|
| `selfhost/lineup.sh` | On the machine | Operator tool: a numbered menu, or `doctor`, `install`, `update`, `backup`, `restore`, `status` as arguments. Bash only, needs Docker plus `curl` or `wget`. Messages in Hungarian (default) and English (`selfhost/messages/hu.sh`, `en.sh`, same keys). Never prints a secret |
| `task deploy` | A developer machine | `task deploy -- --cloud` triggers the cloud deploy workflow and watches it; `--local` runs `./lineup.sh update` on the machine over SSH (`LINEUP_SELFHOST_SSH`, `LINEUP_SELFHOST_DIR`, read from the environment or from the private file `~/.config/lineup/selfhost.env`, mode 600). Asks for a typed `yes` unless `--yes` |
| Release | GitHub Actions | A release publishes the two images to GHCR and attaches `selfhost-<tag>.tar.gz` plus its `.sha256` to the GitHub release. A release needs the owner's go-ahead |
| `self-host` skill | Claude Code | Walks a person through the same steps as the guides and drives the two tools above |

`lineup.sh` commands:

| Command | Behaviour |
|---|---|
| `doctor` | Read-only. Architecture, RAM (warns under 2 GB, fails under 1 GB), free disk (warns under 10 GB), Docker running and usable, Compose 2.20 or newer, reach to `ghcr.io` |
| `install [--from-file PATH] [--accept-backup-limits]` | Runs `doctor`. Refuses if `.env` exists (overwriting it would lock out the database). Asks for or reads the public address, tunnel token, Google values and backup folder; `--from-file` refuses a file that is not mode 600 and parses `KEY=VALUE` lines without ever executing them. Shows the backup limits and needs a typed `IGEN` or `YES` unless `--accept-backup-limits`. Generates the passwords and the signing key, writes `.env` with `umask 077`, starts the stack and checks health |
| `update [--version vX.Y.Z]` | See [section 7](#7-updates-and-migrations) |
| `backup` | One backup now (`backup --once`), then lists the files and their size |
| `restore [--date YYYY-MM-DD] [--yes-restore]` | See [section 8](#8-backups-and-restore) |
| `status` | Container states, `/health?db=1`, age of the last backup (warns over 36 hours), free disk, current version, newest release |

---

## 7. Updates and migrations

Updates are pulled by a person on purpose: nothing outside may connect into the machine, and there is no
self-hosted runner. There are **no automatic updates**, so the main operational risk is that nobody runs them
(see the self-hosted section of [[Privacy and Security]]).

`./lineup.sh update`, in order:

1. Refuse without `.env`. Find the target: `--version`, otherwise the newest release from
   `https://api.github.com/repos/LasterBergamot/lineup/releases?per_page=1`. It does **not** use `/releases/latest`,
   because pre-1.0 releases are marked pre-release and `/latest` skips them. Exit if already current.
2. Download `selfhost-<tag>.tar.gz` and its `.sha256`, verify with `sha256sum -c`, stop on a mismatch.
3. Take a backup (`backup --once`). If it fails, **stop**: no update without a fresh backup.
4. Record the current Alembic revision (`docker compose run --rm --entrypoint alembic migrate current`).
5. Copy the current files to `previous/`, extract the new ones (never touching `.env` or the backup folder), set
   `LINEUP_VERSION` in `.env` atomically.
6. `docker compose pull`, `docker compose up -d --wait`, then the health check. The `migrate` service runs the new
   release's migrations on start.
7. On failure, compare the Alembic revision with step 4:
   - **Unchanged:** put `previous/` back, restore `LINEUP_VERSION`, start again, and say the update was undone and
     nothing was lost.
   - **Changed:** do **not** guess. The migrations have already altered the database, and the old code may not work
     with the new schema, so the script explains that the database changed and that `./lineup.sh restore --date <today>`
     returns to the backup from step 3, then leaves it to the operator.

**When an automatic undo is impossible:** exactly when the migrations ran (the revision changed) and the new version
then failed. The script never tries to guess a downgrade; the pre-update backup is the way back.

---

## 8. Backups and restore

**Limits** (shown at install and repeated in the guides and in `README.md`, in both languages):

> Backups run every night and are kept for 30 days, in a folder on this same machine. They are **not
> encrypted**, and anyone with access to this machine can read them. They protect against mistakes and bad
> updates. **If this machine is lost or fails, all data is lost**, unless someone has copied the backup folder
> elsewhere by hand. Also save the `.env` file somewhere safe and private: without it a restore on a new machine
> means everyone's sign-in and database passwords must be set up again.

This was a deliberate choice (decision S10 in the plan): the data has no special categories, but may include minors'
names, and a backup is only as safe as the machine it lives on. A full-disk-encrypted machine is recommended.

**Format.** The `backup` service wakes at `BACKUP_HOUR` (UTC) and, for each night, writes two PostgreSQL custom-format
dumps (`pg_dump -Fc`) as the superuser:

- `lineup-<date>.dump`: the whole `lineup` database;
- `auth-<date>.dump`: the `auth` database **without the data of four tables**: `auth.sessions`, `auth.refresh_tokens`,
  `auth.one_time_tokens` and `auth.flow_state` (the table definitions are kept). These are the token-bearing tables out
  of the 27 that Auth keeps. A stolen backup therefore cannot be used to take over a signed-in session, and a restore
  simply signs everyone out.

Each dump is first written to a `.tmp` name. Only when **both** succeed are they renamed, and the current time is
written to `last-success`; only then are `*.dump` files older than `BACKUP_RETENTION_DAYS` (30) deleted. A failure logs
the fact without any SQL detail and leaves older backups alone. The folder is owned by the `postgres` user (uid 999)
with mode 700. If a Supabase Auth upgrade adds a token table, re-check this list (the spike that produced it is #252).

**Restore** (`./lineup.sh restore`): lists the available dates; warns that everything after the date is lost and
everyone must sign in again; requires a typed `VISSZAALLIT` or `RESTORE` unless `--yes-restore` is passed; takes a safety
backup first; stops `web`, `api` and `auth`; runs `pg_restore --clean --if-exists` for both databases as the superuser,
**without `--no-owner`**, because `lineup_app` and `supabase_auth_admin` must keep their rights; starts everything and
checks health. Restoring onto a **new machine** is not automated: it needs the backup folder and the saved `.env`.

---

## 9. Limits and gotchas

- **Cloudflare's proxy timeout versus the PDF limit.** The API gives LibreOffice up to 120 seconds
  (`CONVERSION_TIMEOUT_SECONDS`), and Cloudflare answers with a 524 error when the origin does not respond within its
  proxy read timeout. The plan assumed 100 seconds for the free plan; the current Cloudflare documentation (error 524)
  states a default of 125 seconds, raisable only on Enterprise. Re-check the current figure when this matters. It is
  normally irrelevant: a PDF takes seconds.
- **Cloudflare sees all traffic decrypted**, including lineup data and invite codes in URLs, because it terminates TLS
  for the domain. That is more than it sees in the cloud install; see the self-hosted section of
  [[Privacy and Security]].
- **Analytics and rewriting features stay off** (ePrivacy, requirement G14): Web Analytics, Rocket Loader, Email
  Address Obfuscation, Bot Fight Mode and Zaraz. The app uses no analytics, cookies or third-party assets; the guides
  tell operators to keep it that way.
- **`AUTH_JWT_KEYS` is JSON**, so its line in `.env` must be single-quoted.
- **Memory.** The spike measured Auth at about 14 MiB and Postgres at about 40 MiB idle; the PDF conversion (LibreOffice)
  is what needs headroom, hence the 2 GB minimum and `PDF_MAX_CONCURRENT=1`.
- **Architecture.** Images are built for the machine's architecture (`amd64` or `arm64`); `doctor` reports it.

---

## 10. How CI tests it

- The **Self-hosted stack (report only)** job in `.github/workflows/ci.yml` runs `task selfhost:test`
  (`scripts/selfhost_e2e.py`). It is `continue-on-error` at first and has no path filter, because it is meant to
  become a required check once it has proven stable.
- The script writes a throw-away `.env` with generated secrets, starts `selfhost/compose.yml` plus the test overlay
  `selfhost/compose.test.yml` (which builds the local code, publishes `web` on `127.0.0.1:8088` and enables password
  sign-in so no Google is needed) as project `lineup-selfhost-test`, signs two users up against the stack's own Auth,
  reuses `scripts/smoke_live.py` against `http://localhost:8088/api`, and asserts: `/auth/v1/admin/users` and
  `/auth/v1/signup` are 404, `/api/docs` is 404, `/join/x` returns the app, a token yields a real PDF, no token is 401,
  a token signed with another key is 401, and only `web` publishes a port (on loopback). It always runs `down -v`.
- Unit-level guards: `backend/tests/test_selfhost_config.py` (compose file and `.env.example`),
  `test_selfhost_e2e_script.py`, and `frontend/src/security-headers.test.ts` (the Caddyfile's headers equal
  `_headers`; no `log` directive; no `admin` route).
- Dependabot watches the images in `selfhost/` and the base images in `frontend/`.

Locally: `task selfhost:test` (needs Docker, takes several minutes).

---

## 11. Not yet implemented in this repo

The guides describe the finished install, from the plan. At the time this page was written, these pieces named above
were **not yet on `develop`**, so treat their exact behaviour and wording as the plan's, and check the file before you
rely on a detail:

- `selfhost/lineup.sh`, `selfhost/messages/` and `selfhost/backup/` (with the `backup` service in `compose.yml`):
  plan task T6.
- `scripts/deploy.py` and `task deploy`: plan task T7.
- The release job that publishes the images and the `selfhost-<tag>.tar.gz` bundle: plan task T5.

When they land, this section should be deleted and the details above re-checked against the code.
