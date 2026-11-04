# Plan: Optional self-hosted deployment

Status: **planned, not started** · Started: 2026-11-04 · Owner: @LasterBergamot · Epic: #250

This is the working plan for adding a second, optional way to run Lineup: on one always-on machine
(a NAS or small server), reachable from the internet, with no Fly.io, Cloudflare Pages or Supabase
project. It is written so that **a cheaper model can execute each task without design decisions**:
every task lists its files, exact behaviour, tests and acceptance. If a task turns out to need a
decision this file does not make, stop and ask (section 2.4). Do not improvise.

Update this file as work lands: tick the box, fill in the PR number, add a row to the progress log
(section 8). Delete the file once everything is done, as with `PLAN.md`.

**Read first, in this order:** this section, section 1, section 2 and then your task in section 6.

---

## 1. Decisions and hard rules

### 1.1 Decisions (made with the owner; do not reopen)

| # | Topic | Decision |
|---|---|---|
| S1 | Relation to the cloud | **Both run, with separate data.** Fly, Pages, Supabase, `compose.yml`, `compose.e2e.yml`, `backend/fly.toml` and `deploy-dev.yml` are not changed by this work |
| S2 | Sign-in | Self-hosted Supabase Auth (`supabase/gotrue`) with **Google login only**. No passwords, no e-mail server. Who may sign in is controlled by Google's test-user list |
| S3 | Access | Cloudflare Tunnel on a newly bought domain. **The machine opens no ports** |
| S4 | Database | Postgres, one server with two databases (`lineup`, `auth`). Auth requires Postgres |
| S5 | Users | A few known people |
| S6 | CI | The existing checks apply to both; one new job tests the self-hosted stack. No cloud/local choice in CI, because CI tests code, not a target |
| S7 | CD | Cloud unchanged. The machine **pulls** released images. Nothing connects into it, and no self-hosted GitHub runner (the repo is public) |
| S8 | Tooling | `task deploy` (menu, `--cloud`, `--local`) on a developer machine; `selfhost/lineup.sh` (menu or commands) on the machine; the `self-host` Claude skill drives both |
| S9 | Updates | One command run by a person, with an automatic backup first. No automatic updates |
| S10 | Backups | Nightly, 30 days, **a folder on the same machine, not encrypted**. Session and refresh tokens excluded. The limits are stated in `README.md`, in the guides and during install |
| S11 | Cloud backups | Stay parked in #164 |
| S12 | GDPR | Self-hosting does **not** remove GDPR (requirement G1). The compliance docs are updated in this work and must be complete before anyone else is invited |
| S13 | Guides | Operator guides in Hungarian and English, written for non-IT readers. Technical docs in English |
| S14 | Operator | Not decided yet, so everything must work for someone with no IT background, with as little manual work as possible |

### 1.2 Hard rules

1. **Privacy of the deployment.** The repo, wiki, issues, commits and PRs are public. Say only "a
   self-hosted machine" or "the machine's owner". Never write who owns or hosts it, where it is, its
   model, its real domain, hostname or IP. Examples use `lineup.example.com`.
2. **Secrets never enter the repo or the conversation.** Agents must not read `selfhost/.env`,
   `~/.config/lineup/` or any `.env`. Scripts consume them without printing them.
3. **The cloud path must keep working.** Every behaviour added to shared code is opt-in through a new
   environment variable or flag. With the variable unset, behaviour is byte-for-byte what it is today.
4. **Repo conventions apply:** 100 % coverage on both sides, docstrings on public Python, `t()` for
   user-facing frontend strings, third-party actions pinned to a SHA, images pinned by digest,
   branch names `feat/<issue>-…`, commit subjects `#N - <imperative summary>`, merge commits only.
5. **Look up, never invent:** digests (`docker buildx imagetools inspect <image>:<tag>`) and action
   SHAs (`gh api repos/<owner>/<name>/git/ref/tags/<tag>`).

---

## 2. How to execute this plan

### 2.1 Models

| Role | Model | Effort | Notes |
|---|---|---|---|
| **Coordinator** | Haiku 5.5 | high | Start with `claude --model haiku --effort high`. Picks tasks, spawns workers, tracks state, reviews results against each task's Acceptance. **Writes no code itself** |
| **Workers** | Haiku 5.5 or Sonnet 5.5 | high | As listed per task in section 4. In the Agent tool: `model: "haiku"` or `"sonnet"`, `effort: "high"` |
| **Last resort** | Opus 5.5 | high | Only after a worker on Sonnet has failed the same task **twice**, or the failure is a security question nobody can settle. Note it in the progress log with the reason |

Rules for the coordinator:
- Run tasks **in parallel with subagents wherever section 3 allows it**. Spawn one worker per task,
  with `isolation: "worktree"`, so parallel workers cannot touch each other's files.
- If a Haiku worker fails a task once, retry on Sonnet with the failure output in the prompt.
- Give each worker this prompt, with the placeholders filled in:

  > You are implementing task `<Tn>` of `self-host-plan.md` in the lineup repo. Read section 1, section
  > 2.2 to 2.5 and the `<Tn>` section of that file, plus `CLAUDE.md` and the rule files that the task
  > names (`.claude/rules/*.md`; a subagent does not load them by itself). Implement exactly what the
  > task says on branch `<branch>` cut from an up-to-date `develop`, run its Verify commands, and open
  > and merge the PR following section 2.3. Report: PR number, what you verified, what you could not
  > verify, and anything you changed from the plan. If the plan does not settle a decision, stop and
  > report it instead of deciding.

- After each wave, the coordinator re-reads the merged result of that wave before starting the next.

### 2.2 Compliance check per task

`CLAUDE.md` requires `compliance-audit quick <issue#>` when work starts. That skill pins Opus, so to
respect 2.1 **do not invoke it through the Skill tool**. Instead the worker reads the quick-mode section
(`.claude/skills/compliance-audit/SKILL.md`, "Q. Quick mode") and `requirements.md` next to it, and
checks the IDs its task lists under **Compliance** in section 6. Put the result, as the skill's short
table, in the PR body. A MUST that is not met stops the task.

### 2.3 Definition of done for every task

Work from these pre-agreed issues may be committed, pushed, PR'd and merged without asking again
(`.claude/context/workflow.md`). Each PR must:

1. Be cut from an up-to-date `develop`, branch `feat/<issue>-<slug>`.
2. Pass, locally, whichever apply: `task lint`, `task test` (100 %), `task test-e2e` (if `backend/Dockerfile`,
   `compose.yml` or the document pipeline changed), `task fe:check` (if `frontend/` changed).
3. Include its docs. Run `scripts/check_docs_touched.sh origin/develop HEAD`. Follow `.claude/context/docs.md`.
4. Check Dependabot as `.claude/context/pr-checklist.md` says. **Report open Dependabot PRs; do not merge
   them**: they need the owner's confirmation.
5. Use `.github/pull_request_template.md`, `Closes #N` for its issue, and end the body with the
   attribution line from the session's system reminder.
6. Be merged with `gh pr merge <n> --repo LasterBergamot/lineup --merge` once required checks are green.
7. Tick this file's checklist (section 4) and add a progress-log row with the real PR number **in the same PR**.
8. Afterwards: `git switch develop && git pull && git branch -d <branch>`.

**Parallel PRs and shared files.** Tasks in the same wave are assigned files that do not overlap, except
`self-host-plan.md` (one line each in sections 4 and 8) and sometimes `README.md`. If a PR conflicts
after another merges: `git merge origin/develop`, keep both sides of those lines, re-run the checks.
Never rebase a pushed branch to do this.

### 2.4 When to stop and ask the owner

Stop and report instead of working around it when:
- T1 fails (this plan's sign-in design depends on it);
- a task needs a change to `compose.yml`, `fly.toml`, `deploy-dev.yml` or Supabase;
- a check would have to be weakened, or a test deleted, to pass;
- a release, branch-protection or secrets change is needed (`workflow.md`: ask first);
- real user data would be involved before the checklist in section 7 is complete.

### 2.5 Architecture

```
Browser ──> Cloudflare ──> cloudflared ──> web (Caddy + built app, :8080)
                                            ├─ /api/*     ──> api (FastAPI + LibreOffice, :8000)
                                            └─ /auth/v1/* ──> auth (Supabase Auth, :9999), allow-listed paths only
                                      db (postgres:17): databases `lineup`, `auth`
                                      migrate (one-shot) · backup (nightly, writes to the backup folder)
```

Why it is shaped this way:
- **No published ports.** Traffic can only arrive through the tunnel, which is what makes
  `CLIENT_IP_HEADER=Cf-Connecting-IP` safe: nobody can reach the API without passing Cloudflare, so the
  header cannot be forged.
- **One origin.** App, API and Auth share one domain, so CORS stays unset, and the frontend's existing
  fallback to `/api` works as it is.
- **Generic images.** The web image has no domain built in (T3), so images can be public without
  revealing where they run.
- **Least privilege.** `api` gets only the `lineup_app` password and sits on an internal network with no
  internet route. `migrate` is the only service with the database superuser password besides `db` and
  `backup`. `auth` has its own role and database.

---

## 3. Order and parallelism

Part M (owner) can start right away and runs alongside T1 to T9. Only T10 needs it finished.

| Wave | Tasks (parallel within a wave) | Needs |
|---|---|---|
| **0** | **M** (owner, manual) · **T1** spike | nothing |
| **1** | **T2** backend · **T3** web image | T1 passed |
| **2** | **T4** stack + CI job | T2, T3 |
| **3** | **T5** release · **T6** `lineup.sh` + backups · **T7** `task deploy` · **T8** guides · **T9** GDPR docs | T4 |
| **4** | **T10** real install | everything above, including M |

---

## 4. Checklist

| | Task | Issue | Worker | PR |
|---|---|---|---|---|
| [ ] | **M** Manual preparation (owner) | #251 | the owner, helped by the `self-host` skill | n/a |
| [x] | **T1** Spike: Auth on plain Postgres | #252 | Sonnet 5.5, high | n/a |
| [x] | **T2** Backend: self-hosted configuration | #253 | Sonnet 5.5, high (security-sensitive) | #264 |
| [x] | **T3** Web image | #254 | Sonnet 5.5, high | #263 |
| [x] | **T4** Compose stack and CI job | #255 | Sonnet 5.5, high | #265 |
| [ ] | **T5** Release publishing | #256 | Haiku 5.5, high | |
| [ ] | **T6** `lineup.sh` and backups | #257 | Sonnet 5.5, high | |
| [ ] | **T7** `task deploy` | #258 | Haiku 5.5, high | |
| [ ] | **T8** Operator guides (HU + EN) and reference | #259 | Sonnet 5.5, high (Hungarian text) | |
| [x] | **T9** GDPR documents | #260 | Sonnet 5.5, high | #269 |
| [ ] | **T10** Real install and verification | #261 | Sonnet 5.5, high, plus the owner's phone checks | |

---

## 5. Part M: manual preparation (do this first)

Everything a human must do is here, at the start, so T1 to T10 can run unattended. Run `/self-host
prepare` to be walked through it. Dashboards change their wording, so look for the closest match. The
few human steps that cannot happen earlier are listed in section 7.

Keep the results in one private file **on your own computer**. Never commit it and never paste it into
a chat:

```bash
mkdir -p ~/.config/lineup && touch ~/.config/lineup/selfhost.env && chmod 600 ~/.config/lineup/selfhost.env
```

### M1. Check the machine

On the machine (terminal or SSH), run:

```bash
uname -m; grep MemTotal /proc/meminfo; df -h .; docker --version; docker compose version
```

Expected: `x86_64` (or `aarch64`), at least 2 GB RAM (4 GB is comfortable), at least 10 GB free, Docker
installed, Compose 2.20 or newer. On a NAS, Docker usually comes from the vendor's app centre.

**Result to record on issue #251:** only the architecture (`amd64`/`arm64`) and the RAM in GB. No
model, no location. T5 needs the architecture. If Docker cannot be installed, or the RAM is below 2 GB,
stop and tell the coordinator: the plan needs rethinking.

### M2. Decide who operates it, and how to reach it

Pick who runs updates and restores. If someone can use SSH, set it up and test `ssh <host> docker ps`
from your computer, then add to the private file:

```bash
LINEUP_SELFHOST_SSH=user@host
LINEUP_SELFHOST_DIR=/path/where/lineup/should/live
```

With no SSH at all, T10 is done by a person following the guide on the machine itself.

### M3. Buy the domain and add it to Cloudflare

1. Create a [Cloudflare](https://dash.cloudflare.com/sign-up) account with a shared or role-based
   mailbox if you have one. Turn on two-factor authentication.
2. Buy a domain, about €10 a year. Cloudflare Registrar is simplest, as no nameserver change is needed.
   If it does not sell the ending you want, buy it elsewhere, add it to Cloudflare and change the
   nameservers as Cloudflare instructs. Choose a name that does not reveal where the machine is.
3. Add to the private file: `PUBLIC_URL=https://<your-domain>` (no trailing slash).

### M4. Create the tunnel

1. Open **Zero Trust** in the Cloudflare dashboard and choose the free plan. Some guides report it asks
   for a card even on the free plan. If so, nothing should be charged on Free; check before confirming.
2. Go to **Networks → Tunnels → Create a tunnel**, type **Cloudflared**, and name it `lineup`.
3. The page shows an install command containing a long token after `--token`. Copy **only the token**
   and add to the private file: `TUNNEL_TOKEN=<token>`. Do not run the command.
4. Add a **Public hostname**: your domain, no subdomain, no path. Service type `HTTP`, URL `web:8080`.
   The tunnel shows as inactive until T10. That is expected.
5. On the domain's settings, turn **off**: Web Analytics, Rocket Loader, Email Address Obfuscation, Bot
   Fight Mode. They inject scripts or block the app's own traffic. Turn **on**: Always Use HTTPS.

### M5. Create the Google sign-in

Use a **new Google Cloud project** (for example `lineup-selfhost`), not the cloud install's project: the
test-user list belongs to the project, so this keeps the two user lists separate.

1. [Google Cloud console](https://console.cloud.google.com/) → New project.
2. **Google Auth Platform → Audience:** External, publishing status **Testing**. Add every allowed
   person under **Test users**. Only these accounts can sign in.
3. **Data access:** only `openid`, `email`, `profile`.
4. **Clients → Create client → Web application.**
   - Authorized JavaScript origin: `https://<your-domain>`
   - Authorized redirect URI: `https://<your-domain>/auth/v1/callback`
5. Add to the private file: `GOOGLE_CLIENT_ID=<id>` and `GOOGLE_SECRET=<secret>`.

### M6. Backups: confirm the limits

Read and accept: backups are a folder on the same machine and are not encrypted. Protects against
mistakes and bad updates. **Losing the machine loses all data.** Anyone with access to the machine can
read them. Choose a folder on a different disk or share if available, and add
`BACKUP_DIR=/path/to/folder` to the private file (default: `./backups`).

### M7. Compliance facts (needed before real data, not before the code)

Decide the values for `[OPERATOR NAME]`, `[OPERATOR ADDRESS]` and `[PRIVACY E-MAIL]`, as listed in
`documentation/Privacy-and-Security.md`, section 1. T9 prepares a processor agreement for the machine's
owner; signing it happens outside the repo and is the owner's step. **Do not put names in any issue.**

### M is done when

Issue #251 has the architecture and RAM recorded, and the private file holds `PUBLIC_URL`,
`TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_SECRET`, and the SSH values if SSH is used. Close the issue.

---

## 6. Tasks

### T1. Spike: Auth on plain Postgres (gate)

**Why:** Supabase documents Auth inside its own stack and gives no official setup for plain Postgres.
Everything else depends on the answers. **No PR**: work in a throw-away folder outside the repo, and
post the results as a comment on the issue. **Compliance:** none (no real data).

Use `supabase/gotrue:v2.197.0` or the newest tag in
[Supabase's compose file](https://raw.githubusercontent.com/supabase/supabase/master/docker/docker-compose.yml),
and `postgres:17`. Init script for the database:

```sql
CREATE DATABASE auth;
\connect auth
CREATE ROLE supabase_auth_admin LOGIN PASSWORD 'spike' NOINHERIT CREATEROLE;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
ALTER ROLE supabase_auth_admin SET search_path = auth;
```

Auth environment for the spike (a Caddy in front serves `/auth/v1/*` on `http://localhost:8088` with the
prefix stripped):

```yaml
GOTRUE_API_HOST: 0.0.0.0
GOTRUE_API_PORT: "9999"
API_EXTERNAL_URL: http://localhost:8088/auth/v1
GOTRUE_DB_DRIVER: postgres
GOTRUE_DB_DATABASE_URL: postgres://supabase_auth_admin:spike@db:5432/auth
GOTRUE_SITE_URL: http://localhost:8088
GOTRUE_URI_ALLOW_LIST: http://localhost:8088/**
GOTRUE_JWT_ADMIN_ROLES: service_role
GOTRUE_JWT_AUD: authenticated
GOTRUE_JWT_DEFAULT_GROUP_NAME: authenticated
GOTRUE_JWT_EXP: "3600"
GOTRUE_JWT_SECRET: <random 64 hex>
GOTRUE_JWT_KEYS: <JSON array, see check 3; T1 confirmed one object: kty, crv, x, y, d, kid, alg, use, key_ops, as `signing_key.py` prints it>
GOTRUE_JWT_ISSUER: http://localhost:8088/auth/v1
GOTRUE_EXTERNAL_GOOGLE_ENABLED: "true"
GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID: fake
GOTRUE_EXTERNAL_GOOGLE_SECRET: fake
GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI: http://localhost:8088/auth/v1/callback
# For the spike and the CI test only, to get a real token without Google:
GOTRUE_EXTERNAL_EMAIL_ENABLED: "true"
GOTRUE_MAILER_AUTOCONFIRM: "true"
```

Answer each with evidence (command + result):

| # | Check | How | Pass |
|---|---|---|---|
| 1 | Auth migrates on plain Postgres | Start it; read its log | Healthy on `/health`, no migration errors. If a role or extension is missing, add the smallest thing that fixes it and record it |
| 2 | Which tables exist | `\dt auth.*` | Record the names; T6 needs `sessions`, `refresh_tokens` and any other token table |
| 3 | ES256 signing key format | Generate with `cryptography` + `jwt.algorithms.ECAlgorithm.to_jwk(private_key)`, add `kid`, `alg: ES256`, `use: sig`, `key_ops: ["sign","verify"]`, wrap in an array | Auth starts and signs with it. Record the exact accepted JSON shape, with made-up values |
| 4 | Public keys | `curl localhost:8088/auth/v1/.well-known/jwks.json` | EC public key only, no `d` |
| 5 | Token claims | `POST /auth/v1/signup`, decode the access token | `alg` ES256, has `kid`, `iss` = `.../auth/v1`, `aud` = `authenticated`, UUID `sub` |
| 6 | Our verifier accepts it | From `backend/`: `verify_token(token, AuthConfig(issuer=..., jwks_url=...), JwksCache(url))` from `lineup.auth.tokens` | Returns the UUID |
| 7 | supabase-js without a gateway | Node script in `frontend/`: `createClient("http://localhost:8088", "placeholder")`, `auth.signInWithPassword`, `auth.getSession` | Works with a placeholder key |
| 8 | Google start | `curl -i "localhost:8088/auth/v1/authorize?provider=google"` | 302 to `accounts.google.com` with the right `redirect_uri` |
| 9 | Which paths the browser calls | Run 7 and 8 and list them. Compare with the allow-list in T3 | List confirmed or corrected |
| 10 | Dump and restore | `pg_dump -Fc` of `auth` excluding token table data, restore into a fresh database as superuser; `/health`; sign in again | Works, roles and ownership intact |
| 11 | Memory | `docker stats --no-stream` with idle Auth and Postgres | Record MB |

**Acceptance:** all pass, results on the issue, and any differences from T2 to T6 noted there and applied
to this file in T2's PR. **If 1, 3, 5, 6 or 7 cannot pass: stop and ask the owner.** The alternatives are
Supabase's own Postgres image for the auth database, or keeping hosted Supabase Auth.

---

### T2. Backend: self-hosted configuration

**Read:** `.claude/rules/backend-api.md`, `backend-db.md`, `backend-tests.md`. **Branch:** `feat/253-selfhost-backend`.
**Compliance:** S1, S3, S6, S8.

**(a) Separate JWKS address.** In `backend/lineup/auth/tokens.py`, `load_config()` keeps deriving the
issuer from `SUPABASE_URL`, and the JWKS URL now also honours `AUTH_JWKS_URL`:

```python
def _read_jwks_url(issuer: str) -> str:
    """Where to fetch the signing keys; by default the issuer's own well-known address.

    A self-hosted install sets `AUTH_JWKS_URL` to the Auth container's address, so the API does not
    go out through the tunnel to reach a neighbour. The public URL stays the issuer, because that is
    what tokens name. Plain `http` is accepted only for localhost or a single-label host (a Compose
    service name, which only exists on the private network). Raises `AuthConfigError` otherwise.
    """
    raw = os.environ.get("AUTH_JWKS_URL", "").strip()
    if not raw:
        return f"{issuer}/.well-known/jwks.json"
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    internal = parsed.scheme == "http" and (host in _LOCAL_HOSTS or (host and "." not in host))
    if (parsed.scheme != "https" and not internal) or not host or parsed.query or parsed.fragment:
        raise AuthConfigError("AUTH_JWKS_URL must be https, or http to an internal host")
    return raw
```

Tests in `backend/tests/test_auth_dependencies.py`: unset gives today's URL; a service name over `http`
is accepted; `http://example.com`, `ftp://auth` and a URL with a query are refused; a refused value
answers 503 through `get_current_user_id`.

**(b) Plaintext Postgres on the private network.** In `backend/lineup/security/config.py`,
`validate_production_config()` accepts a missing `ssl` only with `DATABASE_TLS=internal-network` **and** a
single-label host. Docker's internal network is not reachable from outside, and running TLS there would
mean managing a private CA on the machine:

```python
_INTERNAL_NETWORK = "internal-network"
...
database_tls = env.get("DATABASE_TLS", "").strip()
if database_tls and database_tls != _INTERNAL_NETWORK:
    problems.append("DATABASE_TLS must be internal-network")
...
ssl_mode = url.query.get("ssl") or url.query.get("sslmode")
internal = database_tls == _INTERNAL_NETWORK and bool(url.host) and "." not in url.host
if ssl_mode not in _ACCEPTED_SSL_MODES and not internal:
    problems.append("DATABASE_URL must set ssl=require or ssl=verify-full")
elif ssl_mode == "require":
    ...  # existing warning
```

Also treat `localhost` as *not* internal, so a typo cannot disable TLS on a real connection (add
`and url.host != "localhost"`). Error messages must never contain the URL. Tests in
`backend/tests/test_security.py`: accepted with flag and host `db`; refused with flag and
`db.example.com`, with flag and `localhost`, without the flag, and with another flag value; everything
else unchanged. Update the docstring.

**(c) Bootstrap command.** New `backend/lineup/db/selfhost_bootstrap.py`, run as
`python -m lineup.db.selfhost_bootstrap` by the `migrate` service:

- reads `MIGRATE_DATABASE_URL` and `LINEUP_APP_PASSWORD`; a missing one is exit code 1 with a message
  that names the variable;
- runs `alembic.command.upgrade(alembic.config.Config("alembic.ini"), "head")`;
- then `asyncio.run(set_role_password(url, password))`, **reusing** `set_role_password` from
  `lineup/db/app_role.py`, and `to_asyncpg_url` from `lineup/db/urls.py`. Do not reuse its `.env` rewriting;
- is idempotent, since it re-runs on every start and update;
- catches `Exception` at the CLI boundary and prints only the class name, as `app_role.main` does, because
  driver messages can quote statements.

Tests in `backend/tests/test_selfhost_bootstrap.py` with both calls patched: success order (upgrade before
password), each missing variable, a failure printing only the class name and never the password.

**(d) Signing-key generator.** New `backend/lineup/auth/signing_key.py`, run as
`python -m lineup.auth.signing_key`: prints to stdout the JSON array for `GOTRUE_JWT_KEYS`, in the shape
T1 recorded, using a fresh P-256 key and a random `kid`. Tests in `backend/tests/test_signing_key.py`:
valid JSON, one key, includes `d`, `alg` ES256, and two runs differ.

**Docs in this PR:** `backend/.env.example` (a block for `AUTH_JWKS_URL` and `DATABASE_TLS`, stating they
are for the self-hosted stack), `.claude/rules/backend-api.md` (tokens row, `config.py` row),
`.claude/rules/backend-db.md` (bootstrap), `.claude/context/workflow.md` (env var list), T1's corrections
to this file. Note in `documentation/Current-State-Everything-Else.md` that these exist and why.

**Verify:** `task lint`, `task test`. `python -m lineup.auth.signing_key` from `backend/` prints a key.

**Acceptance:**
- [ ] With neither variable set, behaviour and existing tests are unchanged.
- [ ] Both new settings refuse anything other than the narrow case they exist for.
- [ ] Bootstrap and key generation exist, are tested, and never print a secret.

---

### T3. Web image

**Read:** `.claude/rules/frontend.md`, `container.md`. **Branch:** `feat/254-selfhost-web-image`.
**Compliance:** G14, S10, S11, S6, S13.

**(a) Same-origin auth.** In `frontend/src/auth/config.ts`, add `VITE_AUTH_SAME_ORIGIN`. When it is
`"true"`, the auth URL is the page's own origin and `VITE_SUPABASE_URL` is ignored:

```ts
interface SupabaseEnv {
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
  readonly VITE_AUTH_SAME_ORIGIN?: string;
}

export function readSupabaseConfig(
  env: SupabaseEnv = import.meta.env as SupabaseEnv,
  origin: string = window.location.origin,
): SupabaseConfig {
  const rawUrl = env.VITE_AUTH_SAME_ORIGIN === "true" ? origin : env.VITE_SUPABASE_URL?.trim();
  ...
```

Everything after that line is unchanged, so the https-except-localhost rule still applies. Document the
docstring, `frontend/src/vite-env.d.ts` and `frontend/.env.example`. Add tests beside the existing ones
(`src/auth/supabase.test.ts`): uses the origin, ignores `VITE_SUPABASE_URL`, refuses a non-local `http`
origin, unset behaves as before.

**(b) `frontend/docker/Caddyfile`:**

```caddy
{
	admin off
	auto_https off
	persist_config off
}

:8080 {
	# No `log` directive, on purpose: invite codes are URL path segments and must not reach any log
	# (requirements S4, S8). Caddy writes no access log unless told to.

	@auth path /auth/v1/authorize /auth/v1/callback /auth/v1/token /auth/v1/logout /auth/v1/user /auth/v1/settings /auth/v1/.well-known/jwks.json
	handle @auth {
		uri strip_prefix /auth/v1
		reverse_proxy auth:9999
	}
	# Everything else under Auth, above all /admin, is never reachable from outside.
	handle /auth/v1/* {
		respond 404
	}

	handle_path /api/* {
		reverse_proxy api:8000
	}

	handle {
		root * /srv
		header Strict-Transport-Security "max-age=31536000; includeSubDomains"
		header X-Content-Type-Options "nosniff"
		header Referrer-Policy "no-referrer"
		header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
		header Content-Security-Policy "frame-ancestors 'none'"
		@html path / /index.html
		header @html Cache-Control "no-cache"
		header /assets/* Cache-Control "public, max-age=31536000, immutable"
		try_files {path} /index.html
		file_server
	}
}
```

T1 confirmed this allow-list for a Google-only install (the browser uses `/authorize`, `/logout`, `/token` and `/user`; `/signup` is not needed). Use it as it stands. `/auth/v1/callback` must stay reachable (Google returns to it).

**(c) `frontend/Dockerfile`:** two stages, both pinned by digest (look them up):

```dockerfile
FROM node:lts-slim@sha256:<digest> AS builder
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Public values only. The anon key is a placeholder: self-hosted Auth has no gateway that checks it.
ENV VITE_AUTH_SAME_ORIGIN=true \
    VITE_SUPABASE_ANON_KEY=self-hosted \
    VITE_COLD_START_NOTICE=false
RUN pnpm build

FROM caddy:2-alpine@sha256:<digest> AS runtime
COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv
RUN rm -f /srv/_headers && mkdir -p /tmp/caddy && chown -R 1000:1000 /tmp/caddy
ENV XDG_DATA_HOME=/tmp/caddy XDG_CONFIG_HOME=/tmp/caddy
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://127.0.0.1:8080/"]
```

`frontend/.dockerignore`: `node_modules`, `dist`, `.env`, `.env.*`, `!.env.example`, `e2e`, `test-results`,
`coverage`, `*.md`. It is a security control, like `backend/.dockerignore`. If `pnpm build` needs anything
outside `frontend/`, stop and report.

**(d) Tests.** Extend `frontend/src/security-headers.test.ts`: import `../docker/Caddyfile?raw`, and assert
every header in `_headers` appears in it with the **same value**, so they cannot drift. Add assertions: no
`log` directive; the auth allow-list has no `admin` path; `handle /auth/v1/*` responds 404. Coverage does
not count this file, but the test still runs.

**Docs in this PR:** `.claude/rules/frontend.md` (a Self-hosting bullet), `.claude/rules/container.md` (add
`frontend/Dockerfile`, `frontend/docker/**` to its `paths:` and describe them), `README.md` env table if it
lists `VITE_*`. Extend `code_re` in `scripts/check_docs_touched.sh` with `frontend/(docker/|Dockerfile$)`.

**Verify:** `task fe:check`. `docker build -t lineup-web frontend`, then run it with a stub network:
`docker run --rm -p 127.0.0.1:8090:8080 lineup-web`; `curl -I localhost:8090/join/abc` gives 200 and the
headers; `curl -o /dev/null -w '%{http_code}' localhost:8090/auth/v1/admin/users` gives 404. (A proxied path
gives 502 here because `api` and `auth` do not exist, and Caddy must still start; if Caddy refuses to start
without those hosts, stop and report.)

**Acceptance:**
- [ ] Without the flag, the Pages build behaves exactly as before.
- [ ] The image contains no domain: `grep -r` for any hostname other than third-party library strings finds nothing specific.
- [ ] Deep links work, admin routes are 404, and headers match `_headers` by test.
- [ ] Runs as non-root.

---

### T4. Compose stack and CI job

**Read:** `.claude/rules/container.md`, `backend-tests.md`, `.claude/context/workflow.md` ("Writing
workflows"). **Branch:** `feat/255-selfhost-stack`. **Compliance:** S6, S8, S13.

**(a) `selfhost/compose.yml`** (digests looked up; image versions come from the bundle's `.env`):

```yaml
# The self-hosted Lineup stack. Documentation: documentation/Self-Hosting-Reference.md.
# Nothing here publishes a port: the only way in is the Cloudflare Tunnel.
name: lineup

services:
  db:
    image: postgres:17@sha256:<digest>
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?}
      AUTH_DB_PASSWORD: ${AUTH_DB_PASSWORD:?}
    volumes:
      - lineup-db:/var/lib/postgresql/data
      - ./postgres-init:/docker-entrypoint-initdb.d:ro
    # The official image starts as root to set up its data directory, then drops to `postgres`.
    cap_drop: [ALL]
    cap_add: [CHOWN, DAC_OVERRIDE, FOWNER, SETGID, SETUID]
    security_opt: ["no-new-privileges:true"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d lineup"]
      interval: 5s
      timeout: 5s
      retries: 20
    networks: [internal]
    logging: &logging
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

  migrate:
    image: ghcr.io/lasterbergamot/lineup-api:${LINEUP_VERSION:?}
    command: ["python", "-m", "lineup.db.selfhost_bootstrap"]
    restart: "no"
    depends_on:
      db: {condition: service_healthy}
    environment:
      MIGRATE_DATABASE_URL: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@db:5432/lineup
      LINEUP_APP_PASSWORD: ${LINEUP_APP_PASSWORD:?}
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    networks: [internal]
    logging: *logging

  auth:
    image: supabase/gotrue:<version from T1>@sha256:<digest>
    restart: unless-stopped
    depends_on:
      db: {condition: service_healthy}
    environment:
      GOTRUE_API_HOST: 0.0.0.0
      GOTRUE_API_PORT: "9999"
      API_EXTERNAL_URL: ${PUBLIC_URL:?}/auth/v1
      GOTRUE_DB_DRIVER: postgres
      GOTRUE_DB_DATABASE_URL: postgres://supabase_auth_admin:${AUTH_DB_PASSWORD}@db:5432/auth
      GOTRUE_SITE_URL: ${PUBLIC_URL}
      GOTRUE_URI_ALLOW_LIST: ${PUBLIC_URL}/**
      GOTRUE_LOG_LEVEL: warn
      GOTRUE_JWT_ADMIN_ROLES: service_role
      GOTRUE_JWT_AUD: authenticated
      GOTRUE_JWT_DEFAULT_GROUP_NAME: authenticated
      GOTRUE_JWT_EXP: "3600"
      GOTRUE_JWT_SECRET: ${AUTH_JWT_SECRET:?}
      GOTRUE_JWT_KEYS: ${AUTH_JWT_KEYS:?}
      GOTRUE_JWT_ISSUER: ${PUBLIC_URL}/auth/v1
      GOTRUE_EXTERNAL_EMAIL_ENABLED: ${AUTH_EMAIL_ENABLED:-false}
      GOTRUE_MAILER_AUTOCONFIRM: ${AUTH_EMAIL_ENABLED:-false}
      GOTRUE_EXTERNAL_PHONE_ENABLED: "false"
      GOTRUE_EXTERNAL_ANONYMOUS_USERS_ENABLED: "false"
      GOTRUE_EXTERNAL_GOOGLE_ENABLED: "true"
      GOTRUE_EXTERNAL_GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID:?}
      GOTRUE_EXTERNAL_GOOGLE_SECRET: ${GOOGLE_SECRET:?}
      GOTRUE_EXTERNAL_GOOGLE_REDIRECT_URI: ${PUBLIC_URL}/auth/v1/callback
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9999/health"]
      interval: 10s
      timeout: 5s
      retries: 10
    # `egress`: Auth must reach Google to exchange the sign-in code.
    networks: [internal, egress]
    logging: *logging

  api:
    image: ghcr.io/lasterbergamot/lineup-api:${LINEUP_VERSION}
    restart: unless-stopped
    depends_on:
      migrate: {condition: service_completed_successfully}
      auth: {condition: service_healthy}
    environment:
      ENV: production
      DATABASE_URL: postgresql+asyncpg://lineup_app:${LINEUP_APP_PASSWORD}@db:5432/lineup
      DATABASE_TLS: internal-network
      SUPABASE_URL: ${PUBLIC_URL}
      AUTH_JWKS_URL: http://auth:9999/.well-known/jwks.json
      APP_BASE_URL: ${PUBLIC_URL}
      CLIENT_IP_HEADER: Cf-Connecting-IP
      PDF_MAX_CONCURRENT: "1"
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    networks: [internal]
    logging: *logging

  web:
    image: ghcr.io/lasterbergamot/lineup-web:${LINEUP_VERSION}
    restart: unless-stopped
    depends_on:
      api: {condition: service_started}
      auth: {condition: service_healthy}
    read_only: true
    tmpfs: [/tmp]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    networks: [internal, edge]
    logging: *logging

  cloudflared:
    image: cloudflare/cloudflared:<version>@sha256:<digest>
    profiles: [tunnel]
    restart: unless-stopped
    command: ["tunnel", "--no-autoupdate", "run"]
    depends_on:
      web: {condition: service_healthy}
    environment:
      TUNNEL_TOKEN: ${TUNNEL_TOKEN:-}
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    networks: [edge]
    logging: *logging

volumes:
  lineup-db:

networks:
  internal:
    internal: true   # no internet route: db and api cannot call out
  edge: {}
  egress: {}
```

T6 adds the `backup` service. `cloudflared` is behind a profile so tests run without a tunnel; the real
install sets `COMPOSE_PROFILES=tunnel` in `.env`.

Two things to check while building this, since neither can be settled on paper:
- Some Compose versions make `up --wait` fail when a one-shot service such as `migrate` exits, even with
  code 0. If that happens on the minimum version (2.20), use `up -d` and poll the health check, in both
  `scripts/selfhost_e2e.py` and T6's `lineup.sh`. Do not remove `migrate`'s `depends_on` condition.
- `AUTH_JWT_KEYS` is JSON, so its line in `.env` must be single-quoted (`AUTH_JWT_KEYS='[{...}]'`).
  Confirm that Auth receives it intact.

**(b) `selfhost/postgres-init/01-databases.sh`** (runs only on an empty volume, mode 755):

```bash
#!/bin/bash
# Creates the two databases on first start. Docker runs this only when the data volume is empty.
set -euo pipefail
psql -v ON_ERROR_STOP=1 -v auth_password="$AUTH_DB_PASSWORD" --username postgres <<'SQL'
CREATE DATABASE lineup;
CREATE DATABASE auth;
\connect auth
CREATE ROLE supabase_auth_admin LOGIN PASSWORD :'auth_password' NOINHERIT CREATEROLE;
CREATE SCHEMA auth AUTHORIZATION supabase_auth_admin;
ALTER ROLE supabase_auth_admin SET search_path = auth;
SQL
```

Add whatever else T1 found necessary. `lineup_app` is created by the Alembic migration, password set by bootstrap.

**(c) `selfhost/.env.example`**: every variable above with a comment and a fake value
(`PUBLIC_URL=https://lineup.example.com`). Say that `lineup.sh install` writes the real file. Add
`selfhost/.env`, `selfhost/backups/` to `.gitignore` (`.env` already matches). Add `Read(./selfhost/.env)` to
the deny list in `.claude/settings.json`.

**(d) `selfhost/compose.test.yml`**: a test overlay, not shipped in the bundle. Builds local images
(`build: ../backend`, `build: ../frontend`, for `migrate`, `api`, `web`), publishes `web` on
`127.0.0.1:8088:8080` with `ports:`, and sets `AUTH_EMAIL_ENABLED=true`.

**(e) `scripts/selfhost_e2e.py`** + `task selfhost:test`. Stdlib only, like `scripts/smoke_live.py`. It:
1. writes a throw-away `.env` to a temp dir with generated secrets, `PUBLIC_URL=http://localhost:8088`, fake
   Google values and no tunnel token;
2. runs `docker compose --env-file <tmp> -f selfhost/compose.yml -f selfhost/compose.test.yml -p lineup-selfhost-test up -d --build --wait`;
3. signs up two users through `POST /auth/v1/signup` and writes their access tokens to 600-mode temp files;
4. **reuses** `scripts/smoke_live.py --base-url http://localhost:8088/api --token-file … --second-token-file …`,
   the existing single definition of the smoke test. Do not re-type those steps;
5. asserts: `GET /auth/v1/admin/users` is 404; `/join/x` returns the app; `POST /api/lineups` with a token and
   a valid body returns a real `application/pdf`; a token signed by a different key is 401;
6. always runs `down -v` and removes the temp files, and never prints a token or password.

T6 extends it with backup and restore. Tests in `backend/tests/test_selfhost_e2e_script.py` for its helpers.

**(f) CI.** New job in `.github/workflows/ci.yml`, modelled on `frontend-e2e`:

```yaml
  selfhost:
    name: Self-hosted stack (report only)
    runs-on: ubuntu-latest
    # Report only at first: must not block a PR until proven stable. No path filter: it is meant to
    # become a required check, and a filtered job would never report.
    continue-on-error: true
    steps:
      - uses: actions/checkout@<same SHA as the other jobs>  # v7
      - name: Install uv
        uses: astral-sh/setup-uv@<same SHA>  # v7
        with:
          enable-cache: true
      - name: Install Task
        uses: arduino/setup-task@<same SHA>  # v3.0.0
        with:
          version: 3.x
          repo-token: ${{ secrets.GITHUB_TOKEN }}
      - name: Start the stack, sign in through real Auth, generate a PDF
        run: task selfhost:test
```

Keep `backend/tests/test_ci_workflow.py` passing. Run actionlint and yamllint as `workflow.md` says.

**(g) Guard test `backend/tests/test_selfhost_config.py`**, in the style of `test_fly_config.py`. Parse YAML
with `yaml` only if already a dev dependency; otherwise check text, as `test_versioning.py` does. Assert for
`selfhost/compose.yml`: no `ports:`; no `build:`; every third-party image has `@sha256:`; every service has
`cap_drop`; `no-new-privileges` on all; `api` is on `internal` only; `ENV: production`; `internal: true`; no
literal secret values (only `${…}`). For `.env.example`: only `example.com` hosts, and no value longer than
40 characters that looks like a real secret. For the whole `selfhost/` tree and `self-host-plan.md`: no
`*.pages.dev`, `fly.dev`, or `supabase.co` addresses of the real cloud project.

**(h) Dependabot** (`.github/dependabot.yml`): add `docker` for `/frontend` and `docker-compose` for
`/selfhost`, grouped and targeting `develop` like the others. Extend `code_re` in
`scripts/check_docs_touched.sh` with `selfhost/`, and add a parametrized case to `TestCheckDocsTouched`.

**Docs in this PR:** new `.claude/rules/selfhost.md` (`paths:` `"selfhost/**"`, `"scripts/selfhost_e2e.py"`),
plus its router row in `CLAUDE.md` (a test requires both); `.claude/context/claude-code.md` map;
`.claude/rules/container.md` (`compose.yml` is not this file); `workflow.md` (task, CI job);
`README.md` (tree, tasks, CI); `documentation/References.md` handwritten tables (Supabase Auth, Caddy,
Cloudflare Tunnel, Postgres image); `documentation/Current-State-Everything-Else.md`. Run `task docs:references`.

**Verify:** `task lint`, `task test`, `task selfhost:test`, actionlint, yamllint. Also check on the host:
`docker compose -p lineup-selfhost-test ps` shows no published ports except the test overlay's.

**Acceptance:**
- [ ] `task selfhost:test` passes locally and in CI, using real Auth tokens and a real PDF.
- [ ] `compose.yml`, `compose.e2e.yml` and `fly.toml` have no diff.
- [ ] The guard test fails if a port is published or an image is unpinned (try it once).

---

### T5. Release publishing

**Read:** `.github/workflows/release.yml`, `backend/tests/test_versioning.py`, `.claude/context/workflow.md`.
**Branch:** `feat/256-selfhost-release`. **Compliance:** S6, S13.

Add a second job to `release.yml`. **Keep the top-level `permissions: contents: write`**, and add
`packages: write` for this job only. Use plain `docker` commands and `github.token`, with no third-party
action and no `secrets.`, so the existing guards in `test_versioning.py` keep their meaning:

```yaml
  publish:
    name: Publish images and the self-hosted bundle
    needs: release
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: write
      packages: write
    env:
      GH_TOKEN: ${{ github.token }}
      VERSION: ${{ needs.release.outputs.version }}
    steps:
      - uses: actions/checkout@<same SHA>  # v7

      - name: Build and push the images
        run: |
          echo "$GH_TOKEN" | docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin
          source_label="org.opencontainers.image.source=https://github.com/$GITHUB_REPOSITORY"
          for pair in api:backend web:frontend; do
            image="ghcr.io/lasterbergamot/lineup-${pair%%:*}:v$VERSION"
            docker build --label "$source_label" -t "$image" "${pair##*:}"
            docker push "$image"
          done

      - name: Attach the self-hosted bundle
        run: |
          echo "v$VERSION" > selfhost/VERSION
          tar --exclude=compose.test.yml --exclude=.env --exclude=backups -czf "selfhost-v$VERSION.tar.gz" selfhost
          sha256sum "selfhost-v$VERSION.tar.gz" > "selfhost-v$VERSION.tar.gz.sha256"
          gh release upload "v$VERSION" "selfhost-v$VERSION.tar.gz" "selfhost-v$VERSION.tar.gz.sha256"
```

The `release` job needs `outputs: {version: ${{ steps.version.outputs.version }}}`. Add `selfhost/VERSION` to
`.gitignore`.

**arm64:** the architecture is on issue #251. If it is `amd64`, stop here. If `arm64`, use a matrix: build
natively on `ubuntu-latest` and `ubuntu-24.04-arm`, push per-arch tags, then
`docker buildx imagetools create` the combined tag. Also add a one-off run of `task test-e2e` on
`ubuntu-24.04-arm` to prove the PDF fidelity tests pass on arm64, because fonts and LibreOffice could differ.
A failure there is a stop-and-ask.

**Test changes in `TestReleaseWorkflow`:** `test_can_write_contents_but_nothing_else` keeps its top-level
check, and add: `packages: write` occurs exactly once, inside `publish`. `test_untrusted_values_never_land_in_a_run_line`
allows `VERSION` under `env:` (`needs.release.outputs.version` is validated semver from the first job). Add:
images use the lowercase `ghcr.io/lasterbergamot/` prefix; the bundle excludes `compose.test.yml` and `.env`.

**Docs:** `.claude/context/workflow.md` ("Versions and releases": images and bundle, and that a release needs
the owner's go-ahead), `README.md` (CI/release).

**Verify:** `task lint`, `task test`, actionlint, yamllint. **Do not run the Release workflow**: T10 does that,
with the owner's go-ahead.

**Acceptance:**
- [ ] Workflow lints; guards pass and cover the new job.
- [ ] Only `publish` holds `packages: write`.
- [ ] arm64 handled per the recorded architecture.

---

### T6. `lineup.sh` and backups

**Read:** `.claude/rules/selfhost.md`, `backend-tests.md`. **Branch:** `feat/257-selfhost-script`.
**Compliance:** G5, G6, S6, S8, S15.

The operator tool. It may be used by someone with no IT background, so: every message says in plain words what
is happening, what went wrong and what to do next. Never show a raw stack trace as the only output. Bash only,
needing nothing but Docker plus `curl` or `wget` for the version check; no `jq`, Python, Task or `openssl` on
the host. Run helpers through the API image when computation is needed. `set -euo pipefail`. Must pass
`shellcheck`. **Never print a secret; never use `set -x`.**

**Layout on the machine** (the extracted bundle):
```
lineup/
├── lineup.sh  compose.yml  postgres-init/  backup/  messages/  VERSION
├── .env            # written by install, mode 600
├── previous/       # last version's files, kept by update
└── backups/        # default BACKUP_DIR
```

**Messages:** `selfhost/messages/hu.sh` and `en.sh` define the same `MSG_*` variables. `LINEUP_LANG` is stored
in `.env`; a test asserts that both files define the same keys. Hungarian is the default.

**Commands.** No argument shows a numbered menu of these. Each also works as an argument. Exit code 0 on
success, non-zero with a clear message otherwise.

| Command | Behaviour |
|---|---|
| `doctor` | Read-only. Reports architecture, RAM (warn under 2 GB; fail under 1 GB), free disk (warn under 10 GB), Docker running, permission to use it, Compose ≥ 2.20, reach to `ghcr.io`. Every line is OK / warning / problem with a fix |
| `install [--from-file PATH] [--accept-backup-limits]` | Runs `doctor`. **Refuses if `.env` exists**, since overwriting it would lock out the database. Asks for or reads `PUBLIC_URL` (must be `https://`, no path), `TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`, `GOOGLE_SECRET` (hidden input), `BACKUP_DIR`. `--from-file` refuses a file that is not mode 600, and parses `KEY=VALUE` lines, **never `source`**. Shows the backup limits (below) and requires a typed `IGEN`/`YES` unless `--accept-backup-limits`. Generates `POSTGRES_PASSWORD`, `AUTH_DB_PASSWORD`, `LINEUP_APP_PASSWORD`, `AUTH_JWT_SECRET` (`docker run --rm --entrypoint python <api image> -c "import secrets; print(secrets.token_hex(24))"`, alphanumeric on purpose, see `backend/.env.example`) and `AUTH_JWT_KEYS` (`python -m lineup.auth.signing_key`). Writes `.env` with `umask 077` to a temp file, then `mv`. Sets `COMPOSE_PROFILES=tunnel`, `LINEUP_VERSION` from `VERSION`. Prepares the backup folder, starts with `docker compose up -d --wait`, then checks health. Ends by saying where the address is and what to save (below) |
| `update [--version vX.Y.Z]` | See below |
| `backup` | `docker compose run --rm backup --once`; reports the files and their size |
| `restore [--date YYYY-MM-DD] [--yes-restore]` | Lists available dates. Warns that everything after that date is lost and everyone must sign in again. Requires typed `VISSZAALLIT`/`RESTORE` unless the flag is passed. Takes a safety backup first. Stops `web`, `api`, `auth`; runs `pg_restore --clean --if-exists` for both databases as superuser, **without `--no-owner`**, because `lineup_app` and `supabase_auth_admin` must keep their rights; starts everything; checks health |
| `status` | Container states; `/health?db=1` (`docker compose exec -T api python -c …`, as in the Dockerfile healthcheck); last backup age from `last-success`, a warning over 36 h; free disk; current version; newest release (see below) |

**`update` steps, in order:**
1. Refuse without `.env`. Find the target: `--version`, otherwise the newest release. Use
   `https://api.github.com/repos/LasterBergamot/lineup/releases?per_page=1`, **not `/releases/latest`**, because
   pre-1.0 releases are marked pre-release and `/latest` skips those. Exit if already current.
2. Download `selfhost-<tag>.tar.gz` and its `.sha256`; verify with `sha256sum -c`; stop on a mismatch.
3. Backup (`backup --once`). If it fails, **stop**: no update without a fresh backup.
4. Record the Alembic revision: `docker compose run --rm --entrypoint alembic migrate current`.
5. Copy the current files to `previous/`, extract the new ones (never touching `.env` or the backup folder),
   set `LINEUP_VERSION` in `.env` atomically.
6. `docker compose pull`, then `docker compose up -d --wait`, then the health check.
7. On failure: compare the Alembic revision with step 4.
   - **Unchanged:** put `previous/` back, restore `LINEUP_VERSION`, start again, and say the update was
     undone and nothing was lost.
   - **Changed:** do not guess. Explain that the database has been changed and `./lineup.sh restore --date <today>`
     returns to the backup from step 3, then leave it to the operator.

**Backup limits text**, shown at install and repeated in the guides and `README.md`, in both languages:
> Backups run every night and are kept for 30 days, in a folder on this same machine. They are **not
> encrypted**, and anyone with access to this machine can read them. They protect against mistakes and bad
> updates. **If this machine is lost or fails, all data is lost**, unless someone has copied the backup folder
> elsewhere by hand. Also save the `.env` file somewhere safe and private: without it a restore on a new machine
> means everyone's sign-in and database passwords must be set up again.

**Backup service.** Add to `selfhost/compose.yml`:

```yaml
  backup:
    image: postgres:17@sha256:<same digest as db>
    restart: unless-stopped
    user: "999:999"   # the image's `postgres` user; install gives this user the backup folder
    entrypoint: ["/backup/backup.sh"]
    depends_on:
      db: {condition: service_healthy}
    environment:
      PGHOST: db
      PGUSER: postgres
      PGPASSWORD: ${POSTGRES_PASSWORD}
      BACKUP_HOUR: ${BACKUP_HOUR:-3}
      BACKUP_RETENTION_DAYS: "30"
    volumes:
      - ./backup:/backup:ro
      - ${BACKUP_DIR:-./backups}:/backups
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    networks: [internal]
    logging: *logging
```

`install` prepares the folder with `docker compose run --rm --user 0 --entrypoint sh backup -c 'chown 999:999 /backups && chmod 700 /backups'`
(this needs `CHOWN`; add it with `--cap-add` on that one command).

`selfhost/backup/backup.sh` (mode 755): with `--once` it runs one backup and exits; otherwise it sleeps until the
next `BACKUP_HOUR` (UTC) in a loop. One backup: `pg_dump -Fc lineup` to `lineup-<date>.dump.tmp`, then
`pg_dump -Fc auth --exclude-table-data=auth.sessions --exclude-table-data=auth.refresh_tokens
--exclude-table-data=auth.one_time_tokens --exclude-table-data=auth.flow_state` (the four token-bearing tables
T1 found, out of 27 in `auth`), to `auth-<date>.dump.tmp`. Only when **both** succeed, `mv` both to their final names and
write the current time to `last-success`. Then delete `*.dump` older than `BACKUP_RETENTION_DAYS`. A failure logs
the fact without any SQL detail, and leaves older backups alone. Excluding token tables means a stolen backup
cannot be used to take over a signed-in session, and a restore simply signs people out.

**Extend `scripts/selfhost_e2e.py`:** after the smoke test, create a team, `backup --once`, delete the team, `restore`
that date non-interactively, confirm the team is back and that signing in again works.

**Tests:** `backend/tests/test_selfhost_script.py`, running the real script with `subprocess` and a **fake `docker`**
placed first on `PATH` (a small shell script that logs its arguments; same idea as the fake `libreoffice` in
`test_pdf_converter.py`), and `tmp_path` as the install dir. Cover: `install` refuses an existing `.env`; `.env` is
mode 600 and contains no value echoed to stdout/stderr; `--from-file` refuses mode 644 and does not execute `$(…)`;
`update` stops when the backup fails, before touching anything; checksum mismatch stops; rollback branch when the
revision is unchanged vs the message when it changed; `restore` refuses without the typed word; menu runs with empty
input; `hu.sh` and `en.sh` have identical keys. Add `shellcheck` for `selfhost/**/*.sh` to the `selfhost` CI job,
through the pinned `koalaman/shellcheck` image.

**Docs:** `.claude/rules/selfhost.md`, `README.md` (a "Self-hosting" section with the backup limits text, as
decision S10 requires), `workflow.md`, `documentation/Privacy-and-Security.md` section 7 (a pointer; T9 writes the rest).

**Verify:** `task lint`, `task test`, `task selfhost:test`, shellcheck.

**Acceptance:**
- [ ] All six commands work through the menu and as arguments, in both languages.
- [ ] No secret appears in any output, including on failure (tested).
- [ ] Backup, wipe, restore works in CI, and signing in works after a restore.
- [ ] A failed update never leaves the app broken without a message saying exactly what to do.

---

### T7. `task deploy`

**Read:** `.claude/context/workflow.md`, `scripts/bump_version.py` (style), `backend/lineup/db/app_role.py`
(`confirm_rotation`). **Branch:** `feat/258-task-deploy`. **Compliance:** S6.

New `scripts/deploy.py` (stdlib only), and in `Taskfile.yml`:

```yaml
  deploy:
    desc: "Deploy to the cloud or the self-hosted machine: task deploy [-- --cloud|--local] [--yes]"
    cmd: python3 scripts/deploy.py {{.CLI_ARGS}}
```

Behaviour:
- `--cloud` and `--local` are mutually exclusive. `--yes` skips the confirmation.
- **No target flag:** if stdin is a terminal, ask `1) cloud 2) local`. If not, print a usage error and exit 2. Never guess.
- **Confirm** with a typed `yes`, saying what will happen, unless `--yes`. End of input counts as no (same as
  `confirm_rotation`). Exit 1 with `Aborted: nothing was changed.`
- **Cloud:** `gh workflow run deploy-dev.yml --ref develop`, wait about 5 s, get the id with
  `gh run list --workflow=deploy-dev.yml --branch develop --limit 1 --json databaseId --jq '.[0].databaseId'`, then
  `gh run watch <id> --exit-status`. Exit with its status. A missing `gh` gives a clear message. A normal push to
  `develop` still deploys by itself; this is for a deliberate manual run.
- **Local:** read `LINEUP_SELFHOST_SSH` and `LINEUP_SELFHOST_DIR` from the environment, otherwise from
  `~/.config/lineup/selfhost.env` (parse `KEY=VALUE` lines, never execute; refuse if not mode 600; ignore other keys;
  never print the values). Refuse an SSH target starting with `-`. Run
  `["ssh", target, "--", f"cd {shlex.quote(dir)} && ./lineup.sh update"]`. Pass `--version` through if given. Missing
  values: tell the user to follow `self-host-plan.md` M2, or run `./lineup.sh update` on the machine itself.
- All subprocess calls use argument lists, never `shell=True`.

Tests: `backend/tests/test_deploy_script.py`, loading the script as `test_versioning.py` loads `bump_version.py`, with
`subprocess.run` patched. Cover every branch above, including non-terminal stdin, no flag, end of input, and a target
of `-oProxyCommand=x`. `scripts/` is outside `--cov=lineup`, but test it fully anyway.

**Docs:** `.claude/context/workflow.md` (Tasks), `README.md` (tasks table), `documentation/Current-State-Everything-Else.md`.

**Verify:** `task lint`, `task test`; `task deploy < /dev/null` exits 2 and does nothing.

**Acceptance:**
- [ ] Nothing runs without a target and a confirmation.
- [ ] Host and paths never appear in output or in the repo.

---

### T8. Operator guides and reference

**Read:** `.claude/rules/documentation.md`, `.claude/context/docs.md`, part M above. **Branch:** `feat/259-selfhost-guides`.
**Compliance:** G14 (the guides must say which analytics to keep off). No code.

Create three pages. Each new file needs its `# Title` and a `[[Title]]` link from `documentation/Home.md`, and a row in
`.claude/context/docs.md`. A test enforces the first two:

| File | `# Title` | Audience |
|---|---|---|
| `documentation/Self-Hosting-Guide.md` | `Self-Hosting Guide` | Non-IT readers, English |
| `documentation/Sajat-Gepes-Telepites.md` | `Saját gépes telepítés` | Non-IT readers, Hungarian. Same content and order |
| `documentation/Self-Hosting-Reference.md` | `Self-Hosting Reference` | Developers, English |

**Both guides** are written so someone who has never used a terminal can follow them:
- Start with what this is, what you will end up with, how long it takes, what it costs (the domain), and who should do
  the first setup: it involves accounts and copying values, so a careful person is enough, but set aside an hour.
- Explain each unfamiliar word the first time: terminal, Docker, domain, tunnel, backup.
- Every step has three parts: **Do** (exact clicks or a command to copy), **You should see**, **If not** (the most
  likely cause and fix).
- Sections: Before you start (M1 to M6, reused from part M, not rephrased in substance); Install; Check it works; Add or
  remove a person (Google test users); Everyday: nothing needs doing, but check `status` monthly; Update; Backups: **the
  limits text from T6, word for word**, how to copy the folder elsewhere by hand; Restore; When something is wrong (a table:
  symptom → what to do → when to ask for help, including "Sign-in says access blocked" = not on the test-user list, and
  "The site is unreachable" = machine off or tunnel down).
- No screenshots, because dashboards change. Name the buttons, and say "look for the closest wording".
- No real domain, host or person; `lineup.example.com` only. Hungarian must read naturally: follow `documentation/Privacy-Notice.md`'s
  style, and do not translate word for word.

**Reference page:** the architecture diagram and the *why* from section 2.5; every service and environment variable; the
network layout; how upgrades and migrations work and when an automatic undo is impossible; the backup format and exactly
which tables are excluded; a note that Cloudflare's free plan has a 100-second proxy timeout while the PDF limit is 120
seconds, normally irrelevant since a PDF takes seconds (verify the current limit); how CI tests it; and how it differs
from the cloud install. Add it to `documentation/Newcomer-Guide.md` as a short section, and to
`documentation/Roadmap-Everything-Else.md` move the "planned" note to done.

**Verify:** `task test` (wiki page tests). A second person-simulation: a fresh worker reads the guide and lists every step
that assumes knowledge not given; fix those.

**Acceptance:**
- [ ] Hungarian and English cover the same steps in the same order.
- [ ] Backup limits are worded as in T6, in README, both guides and the installer.
- [ ] `grep` finds no real domain, host or names.

---

### T9. GDPR documents

**Read:** `documentation/Privacy-and-Security.md` in full, `.claude/skills/compliance-audit/requirements.md`, the task's
pages. **Branch:** `feat/260-selfhost-compliance`. **Compliance:** G1, G4, G5, G9, G10, G14, S15 (this task is that work).

Wording is generic throughout: "the operator", "the machine's owner". ⚖ marks what a lawyer should read. This is
engineering documentation, not legal advice.

`documentation/Privacy-and-Security.md`: add **section 11, "Self-hosted installs"**, keeping sections 1 to 10 as the cloud
source of truth. It must state:
- **Roles.** Clubs remain controllers; the operator remains processor and account controller. **The machine's owner**, if
  different from the operator, can physically reach the data and is a processor or sub-processor (⚖), so an Art. 28
  agreement is needed. Household exemption still does not apply (G1).
- **Inventory differences.** Same data as 2.1, stored on the machine. **New:** the `auth` database holds what section 2.2
  says Supabase holds: e-mail, name, picture URL, Google id, sessions, refresh tokens, sign-in IP and browser. List its
  tables (27 in `auth`; the token-bearing ones are `sessions`, `refresh_tokens`, `one_time_tokens`, `flow_state`, from T1). Backups contain everything except session and token tables.
- **Sub-processors.** Removed: Supabase, Fly.io, Cloudflare Pages. **Cloudflare (Tunnel):** now sees **all traffic
  decrypted, including lineup data and invite codes in URLs**, which is more than it sees in the cloud install; no EU pinning
  on the free plan; DPF + SCCs. **Google:** independent controller for sign-in. **GitHub/GHCR:** images only, no user data.
  The machine's location must be recorded by the operator, privately, and must be in the EU/EEA (G10).
- **Backups (S15).** Same machine, 30 days, not encrypted; deliberate choice, recorded with its reasoning: lower-risk data
  (no special categories) but possibly minors' names, and the backup is only as safe as the machine. ⚖ for a lawyer. A
  restore is tested in CI and once on the real install. Erasure: deleted data survives in backups up to 30 days, which
  matches the notice.
- **Logs.** No access logs in Caddy or uvicorn; Auth at `warn`; Docker log rotation 10 MB × 3.
- **Security measures (Art. 32).** No open ports, network segmentation, least-privilege roles, secrets in a mode-600 file,
  no automatic updates so **someone must run updates**: name this as the main operational risk.
- **Pre-invite checklist** for this variant, including the agreement with the machine's owner, full-disk encryption on the
  machine if the hardware supports it (recommended, because backups are not encrypted), and restore tried once.

Also:
- `documentation/Privacy-Notice.md`: an alternative sub-processor paragraph for self-hosted installs, HU and EN.
- `documentation/Terms-and-Processor-Agreement.md`: a generic processor agreement template between the operator and the
  machine's owner (subject, duration, confidentiality, security, no access unless needed, breach notice without delay,
  return or deletion on ending). `[…]` placeholders only.
- `documentation/Compliance-Records.md`: Art. 30 variant, updated DPIA screening.
- `documentation/Breach-Runbook.md`: self-hosted steps: lost or stolen machine, compromised tunnel token, leaked `.env`
  (what to rotate and how).
- `.claude/skills/compliance-audit/requirements.md`: note that a self-hosted install has its own sub-processor list.

**Verify:** `task test`; `grep -rn` over the changed pages for real names and domains finds nothing.

**Acceptance:**
- [ ] Section 11 covers each bullet above.
- [ ] The processor agreement exists as a template with placeholders only.
- [ ] No page implies self-hosting removes GDPR.

---

### T10. Real install and verification

**Needs:** everything above, M complete. **Read:** the guides and the `self-host` skill. **Worker:** Sonnet 5.5, high.
**Compliance:** full pre-invite checklist before real data (section 11 of the privacy page).

1. **Ask the owner for go-ahead to release** (a release needs it: `workflow.md`). `task release:bump -- minor` in a PR,
   merge, run `Release` from `develop`, and check that images and bundle are attached.
2. Test an anonymous pull: `docker logout ghcr.io; docker pull ghcr.io/lasterbergamot/lineup-web:vX.Y.Z`. If denied, ask the
   owner to set both packages to **Public** (section 7).
3. With SSH (M2): copy the bundle and the private file to the machine with `scp`, run
   `./lineup.sh install --from-file <file> --accept-backup-limits` (the owner already accepted in M6), then **delete the
   copied file**. Do not print its contents. Without SSH: a person follows the guide.
4. Automated checks, from your own computer: `curl -I https://<domain>/` gives 200 and the security headers; `/join/x` gives
   the app; `/auth/v1/admin/users` gives 404; `/api/docs` gives 404; `/api/health?db=1` gives 200. **On the LAN:** `nmap` or
   `curl` against the machine finds no Lineup port. `./lineup.sh status` is healthy. Reboot the machine and confirm
   everything returns. Next morning, confirm the nightly backup appeared. Run a restore. Tag a following patch release and
   run `task deploy -- --local` to prove update works.
5. Hand section 7's phone checks to the owner.
6. Fix anything the guide got wrong. Re-read the `self-host` skill and correct it. Never put the real domain in a commit.
7. When all is done, **delete `self-host-plan.md`** and move anything still true to the docs. Add a row to `PLAN.md`'s log.

**Acceptance:** every line of section 7 is done, and the guides match what actually happened.

---

## 7. Human steps that cannot move earlier

Everything else is in part M. These need something that only exists later, or a human judgement.

| When | Who | Step |
|---|---|---|
| T10, step 1 | Owner | Go-ahead for the release |
| T10, step 2 | Owner | Only if the anonymous pull fails: GitHub → Packages → `lineup-api` and `lineup-web` → Package settings → Public. The packages do not exist until the first release |
| T10, step 5 | Owner | On a phone: sign in with an allowed Google account; confirm an account **not** on the list is refused; invite a second account by link and join; create a lineup; preview the PDF and compare it with the cloud output |
| After T4 is stable | Owner | Optional: make `Self-hosted stack` a required check (branch protection) |
| Before real data | Owner | Fill in placeholders; sign the processor agreement with the machine's owner, outside the repo; one-time lawyer read of the ⚖ items; complete the checklist in `Privacy-and-Security.md` section 11. **Until this is done, use only made-up data.** |

---

## 8. Progress log

| Date | What | Refs |
|---|---|---|
| 2026-11-04 | Plan written after an interview with the owner; epic and tasks filed; `self-host` skill added. No implementation yet. | #250, PR #262 |
| 2026-11-04 | T1 spike passed: all 11 checks (Auth `gotrue:v2.197.0` on `postgres:17`, 75 migrations, ES256 key, our verifier and supabase-js accept it, dump and restore work; Auth about 14 MiB, Postgres about 40 MiB idle). Corrections applied in T2: four token tables excluded from backups, T3 allow-list confirmed, key shape recorded. | #252, no PR |
| 2026-11-04 | T2 landed: `AUTH_JWKS_URL`, `DATABASE_TLS=internal-network`, `lineup.db.selfhost_bootstrap`, `lineup.auth.signing_key`, with tests and docs. | #253, PR #264 |
| 2026-11-04 | T3 web image: `VITE_AUTH_SAME_ORIGIN`, `frontend/Dockerfile`, Caddyfile, `.dockerignore`, header/route tests. pnpm is installed from `packageManager` with npm because `node:lts` has no corepack. | #254, PR #263 |
| 2026-11-04 | T4 landed: `selfhost/compose.yml` (no published port), Postgres init script, `.env.example`, test overlay, `task selfhost:test` (real Auth tokens, real PDF, reuses `smoke_live.py`), guard test, report-only `selfhost` CI job, Dependabot entries. Changes from the plan: `web` needs `cap_add: [NET_BIND_SERVICE]` (the Caddy binary's file capability); `GOTRUE_JWT_DEFAULT_GROUP_NAME` dropped (unsupported, tokens unchanged); test users sign up straight against Auth from inside the `api` container, because the Caddy allow-list has no `/signup`. | #255, PR #265 |
| 2026-11-04 | T9 landed: `Privacy-and-Security.md` section 11 (roles, `auth` tables, sub-processors, backups, logs, Art. 32 measures, pre-invite checklist), self-hosted paragraphs in the privacy notice (HU + EN), a processor agreement template for the machine's owner, the Art. 30 variant and DPIA screening, self-hosted breach steps, and a note in `requirements.md` (the skill directory is lineup-owned, so it was edited here). Audit-log table contents on a real install are marked to confirm in T10. | #260, PR #269 |
