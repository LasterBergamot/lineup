# Plan: Dev preview — frontend, auth, invitations, dev deployment

Status: **planning** · Started: 2026-10-03 · Owner: @LasterBergamot

This file is the working plan for getting Lineup from "a backend that runs on my machine" to
"a web app my teammates can try in a hosted dev environment". It's meant to be picked up at
any time: every phase lists its issues and a checklist, and the **Progress log** at the bottom
records what happened when. Update both as work lands (tick the box, add the PR number).

---

## 1. Why, and what "done" looks like

Today we have a FastAPI backend (docx → PDF via LibreOffice) and a dev Supabase database, but
no UI, no hosting and no real users. The goal of this plan is a **dev preview**:

- a responsive web UI (phone + PC, no native app) that can use every API endpoint, including
  in-page previews of generated lineups,
- Google sign-in (Supabase Auth) with real teams, members and invitations, so real-world
  teammates share one roster and set of lineups,
- the API on Fly.io and the UI on Cloudflare Pages, deployed automatically from `develop`,
- one acquaintance invited and actually using it.

There is **no production environment planned** (amended 2026-10-31): the app runs as one hosted
dev/test deployment for a small group of known users. Prod items and other later work sit in
milestone **"Mx – Parked"** (for example #39, #45, #74); they stay open and can be picked up later.

**Ordering constraint:** a public URL must not exist before real auth. Today
`get_current_user_id()` returns `None`, so everyone sees and edits everything. Auth comes
before the public deploy, and the public deploy comes before inviting anyone.

---

## 2. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | **One hosted environment: dev/test.** The app runs as a single deployment for a small group of known users. No prod environment is planned, and no separate staging. *(Amended 2026-10-31; was "dev + prod".)* | Decided |
| D2 | **Branches: `develop` → dev, `main` → releases.** Feature branches PR into `develop` (the default branch). A release is a `develop` → `main` PR, which later tags a version (#17). Hotfixes branch off `main` and are merged back into `develop`. | Decided |
| D3 | **Monorepo with `backend/` and `frontend/` at the root** (see §4). | Decided |
| D4 | **FE stack:** React + TypeScript + Vite, Tailwind, shadcn/ui, TanStack Query, React Router, React Hook Form + Zod, react-i18next (D12), client generated from `/openapi.json` (openapi-typescript + openapi-fetch), pdf.js for previews, Vitest + Playwright. | Decided |
| D5 | **Hosting:** API on Fly.io (scale to zero), FE on Cloudflare Pages. | Decided |
| D6 | **Auth:** Google OAuth through Supabase Auth. The FE uses `@supabase/supabase-js` for sign-in only; all data goes through FastAPI. The API validates the JWT against the project's JWKS. | Decided |
| D7 | **Dev behaves like prod** (same sign-in and invite flow). Access to dev is limited by keeping the Google OAuth consent screen in **Testing** mode, with a list of test users (see §6.4). | Decided |
| D8 | **Supabase free-tier pause:** a GitHub Actions cron runs **twice a week** (Mon + Thu, so one failed run is not enough to let it pause). It starts as `SELECT 1` through the pooler (#156), independent of Fly, and gains `/health?db=1` once the API is deployed. The FE detects a paused DB and says so (see §5.3). | Decided |
| D9 | **Milestones:** **"M3 – Dev preview"** holds the dev-preview work (auth, teams and invitations, UI, dev deployment); **"Mx – Parked"** holds what is deliberately not planned now, prod items included; "M2 – Prod" is closed (D1, amended 2026-10-31). Phase 1 issues stay in M1, since Phase 1 is a subset of it. | Decided |
| D10 | **Team/ownership model:** teams as workspaces, owner + member roles, multi-use invite links, name-only public opponent directory, invite links that expire after 24 h by default (see §6). | Decided |
| D11 | **UI theme: Polaris** (superseded by D14) (tweakcn, shadcn tokens). Its spec lives in `frontend/DESIGN.md`. AstroVista was dropped. | Decided |
| D12 | **UI language: Hungarian by default, English selectable** (react-i18next, #155). Done first in Phase 6 so every new screen uses `t()` from the start; the choice is kept in localStorage under `lineup-lang` (disclose in #94). The `.docx` template and the API are unchanged. Server 422 sentences from the API stay English until the backend returns error codes. | Decided |
| D13 | **Versions: one repo-wide SemVer tag `vX.Y.Z`** for backend and frontend (the FE client is generated from the backend spec, so they move together). A manual `release` workflow bumps `backend/pyproject.toml` and `frontend/package.json`, tags and publishes a GitHub Release; pre-1.0 tags are cut from `develop` when a feature set lands on dev, `v1.0.0`+ from `main`. Images are tagged `lineup:<version>` so an older version can be deployed; going back needs expand/contract migrations (#17). | Decided |
| D14 | **UI design system: Lineup** replaces Polaris (rounded shapes, soft tokens, a text wordmark with an amber dot, an L-tile favicon). Ported in two PRs (#238 foundation, #239 components and screens); the plan is `PLAN-ui-redesign.md`, the spec `frontend/DESIGN.md`. D11 is kept as history. | Decided |

### Supabase JS and the "disabled API"
The setting turned off on the dev project is the **Data API** (PostgREST: auto-generated
REST over the tables). We keep it off, because all data goes through FastAPI. **Supabase Auth
(`/auth/v1`) is a separate service and isn't affected**, so `supabase-js` sign-in works with
the Data API disabled. What does need configuring:
1. Google Cloud console: an OAuth client (web). The authorized redirect URI is
   `https://<project-ref>.supabase.co/auth/v1/callback`.
2. Supabase → Authentication → Providers → Google: enable it and paste the client ID and secret.
3. Supabase → Authentication → URL configuration: the Site URL is the dev Pages URL. Redirect
   allow-list: `http://localhost:5173/**`, the dev Pages URL, and `https://*.<pages-project>.pages.dev/**`
   for PR previews.
4. The FE gets `VITE_SUPABASE_URL` + the **publishable/anon key** (public by design; it only
   allows what Auth and RLS allow).

If we'd rather not ship the full client, `@supabase/auth-js` is the auth-only subpackage. Either is fine.

---

## 3. Phases and issues

Issue numbers marked **new** don't exist yet. Create them with the `new-issue` skill, then
replace "new" with the number here.

### Phase 0 — Branching + repo restructure
- [x] **new** Branching strategy: create `develop` and make it the default branch. Protect both
      branches (PR + green CI required, no force-push). `ci.yml` triggers on both branches;
      `dependabot.yml` gets `target-branch: develop`. Update `CLAUDE.md` (the Dependabot rule
      says "merge `main`"), the `create-pr` and `triage-dependabot` skills (base branch), and
      `documentation/Roadmap-Everything-Else.md`. Refs #17, #8.
- [x] Move the backend into `backend/` (D3, §4). Restructure only, no behaviour change. (branch `chore/86-move-backend-into-backend-dir`, #86, PR #87)
- [x] Amend #13: retitle to "Dev environment on Fly.io", drop "test env", replace Management-API
      auto-resume with the cron (D8).
- [x] Amend #17: record D2 (the release happens on the `develop` → `main` merge).
- [x] Amend #8: narrow to "CD for dev from `develop`". New issue #100: prod CD from `main` (M2).
- [x] Amend #39: split out #101 "Google OAuth + JWKS validation on dev" (M3). #39 keeps the
      prod project and cutover.
- [x] Amend #20: record D3–D5 and turn it into the **Frontend epic**.
- [x] Amend #19, #49, #50 and #51 to match §6 once D10 is confirmed.
- [x] Rename and re-scope the milestones (D9). (#102, PR #103)

### Phase 1 — Backend prerequisites for a browser UI and a public URL
A subset of M1. The rest of M1 follows at its own pace.
- [x] #104 Docs tooling first (PR 0): README/docs gate (CLAUDE.md rule, `create-pr` gate, `docs-check` CI job), Newcomer Guide and References wiki pages (generated dependency block, `task docs:references`). (PR #105)
- [x] #69 `GET /health` (+ `?db=1`): used by Fly, CD, the cron and the FE wake-up banner. (PR #106)
- [x] #56 CORS (origins from an env var) + input limits. (PR #106)
- [x] #53 unknown `team_id` → 500 (PR #107)
- [x] #54 control characters / whitespace-only strings (PR #107)
- [x] #55 stable ordering (UI lists) (PR #107)
- [x] #70 Dockerfile hardening (non-root before going public) (PR #108)
- [x] #71 PDF pipeline robustness (concurrent conversions on a small machine) (PR #108)
- [x] #68 least-privilege DB role + RLS as migrations (PRs #111, #115; applied to dev Supabase and smoke-tested as `lineup_app` on 2026-10-05)
- [x] #60 Alembic migrations in CI (CD will run them) (PR #111)

### Phase 2 — Frontend skeleton (can run in parallel with Phase 3)
- [x] #119 FE skeleton + tooling + CI (PR #123): Vite app in `frontend/`, Tailwind + shadcn with the
      Polaris theme (D11, light + dark), and an app shell (sidebar on desktop, bottom nav on mobile). Also the
      generated API client (a CI check fails if it's stale), `task fe:*` targets, and a CI job
      (lint, typecheck, test, build).
- [x] #120 Cold-start-aware data layer (§5) (PR #126): skeleton loaders, a wake-up banner, retry policy.
- [x] #121 First screen (PR #128): a one-off lineup form calling `POST /lineups` against the local container.
      This meets #20's acceptance.

### Phase 3 — Real auth on dev
- [x] #101 (split from #39) Google provider on the dev Supabase project. `get_current_user_id()`
      validates the JWT via JWKS and returns `sub`. (Code in PR #122; the manual Google Cloud +
      Supabase dashboard setup, see `documentation/Auth-Setup.md`, was done and a real sign-in
      verified on 2026-10-28.)
- [x] #47 fail closed (401 without a valid token) (PR #122)
- [x] #19 `team_members` / `team_invitations` schema (as amended by §6) (PR #125)
- [x] #49 team-scoped access for players and saved lineups (PR #127)
- [x] #48 IDOR on saved-lineup create (PR #127)
- [x] #50 `is_public` semantics (as amended by §6) (PR #127)
- [x] #52 NOT NULL owner/user ids. On dev the existing rows can simply be wiped instead of
      backfilled. (PR #125)
- [x] #129 FE: sign-in page, token on every call, onboarding ("no team yet → create one or
      paste an invite link"). (PR #130; the invite-link field is shown disabled until #51. The
      real Google sign-in was tried on 2026-10-28 after the #101 setup.)
- [x] Run the `supabase-smoke` skill after the model changes (2026-10-28, as `lineup_app`, after
      applying the Phase 3 migrations to the dev Supabase project).

### Phase 4 — Dev deployment + CD
**Compliance gate (#92):** before anyone outside the team gets access to dev, the following
must be done. The users are not from one household, so the household exemption does not cover
them: GDPR applies even at this size.
- #94 GDPR documentation pack (its data inventory and notice must list the browser storage from #155 and the
  rate-limit counters from #96: see the 2026-10-28 comment on #94). *Written (PR #196)*; still open before
  inviting anyone: fill the `[…]` placeholders (operator name, address, privacy e-mail, app URL), accept the Fly.io
  and Cloudflare DPAs, a one-time lawyer/native-speaker read of the ⚖ items and the Hungarian text, and link the
  notice from the sign-in page (#97). The checklist is in `documentation/Privacy-and-Security.md`, section 10.
- #93 Sentry PII scrubbing (required before any `SENTRY_DSN` is set)
- #97 frontend privacy/security baseline

#96 (API hardening) has to land before the public deploy (#13); it is done below.
- [x] #96 API hardening: security headers + `Cache-Control: no-store` on every response, body size
      cap (413), in-memory rate limits on both generate endpoints (429), `POST /lineups` now needs
      sign-in, `/docs` off under `ENV=production`, fail-closed production config. For the Fly
      deploy set `CLIENT_IP_HEADER=Fly-Client-IP` (PR #171). `supabase-smoke` passed against
      the new code on 2026-10-28 (as `lineup_app`).
- [ ] #13 Fly.io app `lineup-dev-lb`: `auto_stop_machines`, `min_machines_running = 0`, ~1 GB RAM
      for LibreOffice. Secrets via `fly secrets`: pooler `DATABASE_URL`, `ENV=production`,
      Supabase JWKS URL, `CORS_ORIGINS`.
      *Config written* (`backend/fly.toml`, region `ams`, runbook `documentation/Fly-Setup.md`); still
      open: the owner creates the app, sets the secrets and runs the first `fly deploy --ha=false`, then this box is ticked. (Done 2026-10-30: the app is deployed and
      `/health?db=1` answers 200; open: DPA, the Fly free trial ends after 2 hours of machine time or 7 days (add credits or a card before then), and the real PDF cold-start test, which passed on 2026-10-30 from the deployed app, #175.) The first deploy created two machines (Fly's HA default); scale to one with `fly scale count 1`. #8's CD must use `--ha=false`.
- [x] #175 FE deploy to Cloudflare Pages: `VITE_API_URL`, `VITE_SUPABASE_URL`,
      `VITE_SUPABASE_ANON_KEY`, and `VITE_COLD_START_NOTICE=true`. Every PR gets a preview URL.
      (Repo side in PR #177; the site is live at `https://lineup-kfi.pages.dev`, built from `develop`, and PR #178 closes it out. Cloudflare added
      `-kfi` because `lineup-dev` was taken. Deep links use Pages' built-in SPA mode, so there is no `_redirects`. Google sign-in works, the
      security headers are live, and the cold-start PDF test passed on 2026-10-30. PR previews cannot sign in, since their origin is not in
      `CORS_ORIGINS`: documented, not loosened. The Cloudflare DPA is left for the compliance gate, like Fly's.)
- [x] #8 CD workflow on push to `develop`: Alembic `upgrade head` (session-pooler URL from GitHub
      secrets), then `flyctl deploy`, then poll `/health?db=1` with a cold-start-tolerant retry,
      then the Pages deploy. If the health check fails, Fly keeps the previous release.
      (`.github/workflows/deploy-dev.yml`, PR #184.) The Pages deploy is not part of it: the
      Pages Git integration already publishes `develop`, so no Cloudflare token is needed in GitHub. The owner set
      the `FLY_API_TOKEN` and `MIGRATE_DATABASE_URL` Actions secrets (`Fly-Setup.md`, *Continuous deployment*) and
      the manual *Deploy dev* run on 2026-10-31 was green (one machine, `/health?db=1` 200). The push trigger
      itself is first exercised by the next merge that changes `backend/`.
- [x] #190 Live smoke test after every dev deploy: `scripts/smoke_live.py` (one definition, also used by the
      `supabase-smoke` skill) and a `smoke` job in `deploy-dev.yml` that runs it as `lineup_app` after the health
      check (PR #195). **Owner to-do:** add the `SMOKE_DATABASE_URL` Actions secret (the `lineup_app`
      transaction-pooler URL, same value as the Fly secret `DATABASE_URL`; `Fly-Setup.md`), run *Deploy dev* once by
      hand, and tick this box when the `smoke` job is green on a clean dev database. (Done 2026-10-31: the owner set
      the secret and the manual *Deploy dev* run 41233261200 was green, `smoke` job included.)
- [x] #156 Keep-alive cron, twice a week (D8, §5.3). It can land before Fly: `SELECT 1` through the pooler
      with a `KEEPALIVE_DATABASE_URL` Actions secret that the owner sets. (Workflow in PR #168; the owner set the secret and
      verified a manual run on 2026-10-28. Glance at the first scheduled Monday/Thursday runs.)
- [x] #17 Tags and releases (D13): the manual `release` workflow, `task release:bump`, a test that the two version files match
      and the API reads its version from `pyproject.toml`. (Two deviations from D13: the bump is a PR, not a workflow commit,
      because protected branches reject a commit that never ran the required checks; and there are no `lineup:<version>` image
      tags, because Fly builds from source, so the git tag is the version handle. Baseline `v0.1.0` cut after the merge.)
- [x] Billing (#13): Fly has **no billing alerts or spending cap** (its docs say so), and the free trial (no card, up to 2 h of
      machine runtime or 7 days) ends soon after the first deploy. Before it ends add prepaid credits (the closest thing to a
      cap) or a card, and check the month-to-date bill in the dashboard now and then. Supabase's free plan can't bill; keep the
      billing email readable. See `documentation/Fly-Setup.md`, *Trial and billing*.

### Phase 5 — Invitations
- [x] #51 endpoints, in the link-based form of §6 (PR #186)
- [x] #189 FE: team members page, "Invite" button (copy link / mobile share sheet),
      `/join/:code` page that survives the Google sign-in round trip. (PR #194; the owner still
      tries a real invite with a second Google account, and the `lineup-return-to` storage entry
      is to be added to the #94 inventory.)

### Phase 6 — Feature-complete UI
- [x] #155 i18n (hu default, en), **first**: the existing screens (sign-in, onboarding, lineup form,
      backend banner) are converted in the same item, so the screens below use `t()` from the start (D12).
      New screens must add their texts to `frontend/src/i18n/locales/{hu,en}.json` (ESLint fails on a
      hard-coded string in a component).
- [x] #197 Roster management (teams, players, opponent directory search): the Roster page with a players card (any member adds, edits, deletes), team settings for owners (rename, directory listing) and a name-only opponent directory search. (PR #198)
- [x] #203 Lineup creator: roster pick or free text, cap-number validation, opponent combobox
      (directory + recent opponents + free text), Preview panel (pdf.js), Save. (PR #207)
- [x] #204 Saved lineups: list (newest first), hover/tap PDF preview cached in memory, generate PDF/DOCX, delete,
      "Clone to new match" (hands only the lineup id to the creator as router state `cloneFromId`; the Lineup page fetches the lineup, #203). (PR #206)
- [x] Mobile polish: Playwright at a phone viewport (`task fe:e2e`, #159; report-only CI job); web-app manifest ("Add to home screen") without a service worker. (PR #209)

**Exit criteria:** an acquaintance signs in on dev via an invite link, sees the shared roster,
creates and previews a lineup on their phone, and feedback is collected.

---

## 4. Repo layout (D3)

```
lineup/
├── backend/                 # everything Python
│   ├── app.py  main.py  pyproject.toml  uv.lock
│   ├── lineup/  tests/  alembic/  alembic.ini
│   ├── resources/  docker/  Dockerfile  .dockerignore
│   └── .env.example         # backend env (DATABASE_URL, ENV, SENTRY_DSN, CORS_ORIGINS…)
├── frontend/                # Vite + React app
│   ├── src/  public/  package.json  pnpm-lock.yaml
│   └── .env.example         # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY…
├── documentation/           # wiki mirror (unchanged)
├── .github/                 # CI/CD for both (path filters per side)
├── Taskfile.yml             # root: `includes:` backend/ and frontend/ Taskfiles
├── compose.yml              # build context ./backend
├── README.md  CLAUDE.md  PLAN.md
```

- Done as **one restructure-only PR before any frontend code**, using `git mv` so history follows
  the files (`git log --follow`).
- Root Taskfile namespaces: `task be:test`, `task fe:dev`, … The existing `task test` / `task lint`
  stay as aliases for the backend. `.claude/settings.json` allows exactly those commands, and
  muscle memory relies on them.
  *As built in the restructure PR:* the Taskfile stays a single root file with the existing task
  names and `dir: backend` on every Python task, so nothing in the allow-list changed. The
  `be:`/`fe:` includes are deferred to the FE skeleton PR.
- *As built:* the real `.env` lives in `backend/.env` (next to `backend/.env.example`; a separate
  `frontend/.env` comes later). `compose.yml` keeps `image: lineup` (no `build:`) and reads
  `env_file: backend/.env` with `required: false`, because Compose's own `.env` interpolation only
  looks next to `compose.yml`. The Docker build context is `backend/` (`docker build -t lineup backend`),
  and `.claude/settings.json` denies reading `backend/.env*` as well.
- Things to update in the same PR: Docker build context, `compose.yml`, CI `working-directory`,
  Dependabot `directory: /backend` (plus `/frontend` npm later), coverage paths, test resource
  paths, the skills, `CLAUDE.md`, `README.md`, `documentation/`, and the e2e task.
- Payoff: CI can path-filter (FE-only changes skip the Python suite and vice versa), and the
  Docker context no longer includes the frontend.

---

## 5. Cold starts in the frontend

Fly scales the API to zero, so the first request after idle waits a few seconds (machine boot
+ Python + imports), and the first PDF waits extra for LibreOffice. The Fly proxy **holds** the
request while the machine boots, so requests mostly get slower rather than failing. The UI is
built around that:

### 5.1 Render static, stream dynamic
- The app shell, navigation, headings, form layouts and empty-state copy are static. Cloudflare
  serves them instantly and they render immediately, without waiting for the API.
- Every data region (rosters, lists, the opponent combobox, previews) is its own TanStack Query
  boundary with a **skeleton placeholder** (shadcn `Skeleton`, a shimmer in the final shape of
  the content). Regions fill in independently as their data arrives. React `Suspense` handles
  route-level code splitting.
- Mutations (save, generate) show an inline spinner on the button and disable it to prevent
  double-submits. The form stays visible and editable.

### 5.2 "Server is waking up" notice
- On app load (even on the sign-in page), the FE fires `GET /health` immediately. That starts
  the machine booting while the user is still signing in, which hides most of the cold start.
- A `BackendStatus` provider tracks `unknown → waking → ready | db-paused | down`. If `/health`
  hasn't answered in ~1.5 s, a non-blocking banner appears: *"The server is starting up — this can
  take up to ~30 seconds on our free hosting. Thanks for your patience."* It shows elapsed time
  and goes away as soon as the API is up.
- PDF generation has its own message after ~5 s: *"Generating the PDF — the first one after a
  break takes a bit longer."*
- The whole notice sits behind `VITE_COLD_START_NOTICE`. On always-on infra later, set it to
  `false` (and eventually delete the component). The skeletons stay either way.

### 5.3 Retries, timeouts, and a paused database
- Query retry policy: network errors and 502/503/504 are retried with backoff for up to ~60 s
  while the status is `waking`. 4xx responses are never retried. Client timeouts are generous
  (PDF ≥ 120 s, matching `CONVERSION_TIMEOUT_SECONDS`).
- **What happens if Supabase pauses anyway?** (Free projects pause after about a week of
  inactivity. The twice-weekly cron (#156) should prevent it, but GitHub disables scheduled workflows in
  repos with no activity for 60 days, and the cron itself can fail.)
  - **Supabase Auth is paused too**, so Google sign-in fails, not just data access.
  - The API stays up: `/health` → 200, `/health?db=1` → 503, DB endpoints → errors. The one-off
    `POST /lineups` (no DB) keeps working for anyone already signed in.
  - The FE maps `/health?db=1` = 503 to the `db-paused` state and shows *"The database is
    paused (free tier). Ask <admin> to resume it."* instead of generic errors.
  - Recovery: Supabase dashboard → Restore project. It takes a few minutes and keeps the data.
    Projects paused for a long time (~90 days) may no longer be restorable from the dashboard,
    only downloadable as a backup. That's why we keep the cron and notice failures.
  - **Emails:** GitHub only emails about a scheduled workflow when a run **fails**. The email
    goes to the user who last changed the workflow's `cron:` line, and only if Settings →
    Notifications → Actions has email turned on (pick "only failed workflows").
  - **The 60-day trap:** the repo is public, so after 60 days without repo activity (commits/PRs;
    the cron's own runs don't count) GitHub disables the scheduled workflow. A disabled workflow
    doesn't fail, it just stops running, so no failure email arrives. Don't rely on a warning
    email either. Mitigations, from cheapest:
    1. Normal development activity resets the clock, so it only matters during long breaks.
    2. After a break, check the Actions tab and re-enable the workflow (one click).
    3. If it ever bites, add a monthly step that re-enables it via `gh workflow enable`, or
       accept a manual DB restore after a long break.

---

## 6. Teams, ownership and invitations (D10 — proposed)

Requirement: real-world teammates share **one** set of data (roster, saved lineups), and other
teams' **names** are public so they can be picked as opponents from a dropdown, with free text
still allowed for teams not in the DB yet.

### 6.1 Model: the team is the workspace
- Everything a club owns (players, saved lineups) **belongs to a team**, and every member of that
  team can see and edit it. That's how Slack/Notion workspaces work, and it's simpler than
  per-user ownership:
  - `Player.team_id` becomes **required**. This removes #49's "team-less players are
    creator-only" special case.
  - `SavedLineup` gets a required **`team_id`** (the workspace it lives in). This is separate
    from the existing soft-reference `source_team_id`/`source_opponent_id`, which stay as
    snapshots.
  - `user_id` on players/lineups becomes `created_by` (audit only, not used for access).
- Access rule everywhere: *the caller is a member of the row's team*. One rule makes the code,
  the tests and the later RLS (#21) simple.
- The one-off `POST /lineups` stays stateless, but since #96 it needs sign-in and is rate limited like the generate endpoint of saved lineups.

### 6.2 Roles: owner + member (drop "admin" for now)
- **member**: full read/write on the team's roster and lineups, and can see the member list.
- **owner**: also invites and removes members, renames, deletes the team, and toggles listing.
  Ownership can be transferred, and the last owner can't leave.
- The schema keeps `role` as a string/enum, so adding `admin` later is cheap. With a handful of
  users per team, a third role adds UI and tests without real benefit yet.

### 6.3 Invitations: multi-use links (easiest, no email infra)
| Option | Flow | Verdict |
|---|---|---|
| **A. Invite link** | The owner clicks "Invite", gets `https://<app>/join/<code>` and sends it on WhatsApp/Messenger. The recipient opens it, signs in with Google, and joins as a member. The link is multi-use, expires (**default 24 h**; the owner can pick 2 h, 24 h or 3 days), can be revoked, and the owner sees who joined. Short expiry limits the damage if a link is forwarded further than intended. | **Chosen** |
| B. Email-bound invite | The owner types an email, and only that Google account can accept. Needs outgoing email (or a manually sent link) and handling of email mismatches. | Later, as an option on A (the `email` column already exists in #19) |
| C. Join request | A user finds the team in the directory, requests to join, and the owner approves. | More UI. Not needed while everyone already knows each other |

Endpoints (amends #51):
- `POST /teams/{id}/invitations` (owner, body `{expires_in_hours: 2 | 24 | 72}`, default 24) →
  `{code, url, expires_at}`
- `GET /teams/{id}/invitations` (owner) / `DELETE …/{inv_id}` (revoke)
- `GET /invitations/{code}` (public preview: team name + inviter; lets the join page say *"Join
  Ferencváros?"* before sign-in)
- `POST /invitations/{code}/accept` (signed in) → adds a membership. Idempotent if already a
  member. 410 if expired/revoked, 404 if unknown.
- `GET /teams/{id}/members`, `DELETE /teams/{id}/members/{user_id}` (owner, or self = leave),
  `POST /teams/{id}/transfer-ownership`.
- Codes are long random tokens (`secrets.token_urlsafe`), so they can't be guessed.

### 6.4 Who can sign up, on dev (and later prod)
- Simulating prod (D7): any signed-in user can create their own team or join one via a link.
  There's no special dev-only code path.
- Restricting **who** can sign in to dev needs no code, using Google's **Testing** mode. Here's
  how it fits together:
  - The allowlist lives in the **Google Cloud console**, not in Supabase: Google Auth Platform
    → Audience. Publishing status stays **Testing**, and **Test users** lists the allowed Google
    accounts (gmail or Google Workspace addresses, up to 100).
  - Flow: the user clicks "Sign in with Google" in our UI → supabase-js redirects to Google →
    Google checks the test-user list. Listed users see a one-time *"Google hasn't verified this
    app"* screen, click Continue, consent, and land back in the app signed in. Anyone else is
    stopped by Google itself (*"Access blocked … error 403: access_denied"*) and never gets a
    Supabase session.
  - So adding someone = adding their Google address in the console (takes effect immediately).
    Removing them blocks new sign-ins, but an existing Supabase session stays valid until it
    expires. To cut someone off immediately, also delete the user under Supabase →
    Authentication → Users.
  - Supabase itself has no email allowlist for OAuth. A Supabase-side alternative is turning
    off "Allow new users to sign up" and creating/inviting each user from the dashboard. More
    clicks, same result, so we use the Google list.
  - For prod, decide later between publishing the consent screen (open sign-up; only basic
    scopes are requested, so Google's verification is light) and an email allowlist in the API.

### 6.5 Opponents: name-only public directory + free text
- `is_public` is reinterpreted as **"listed in the opponent directory"**. A listed team exposes
  **only `id` + `name`** via `/teams/pool`, never its roster or lineups. Since listing reveals
  only a name, it can default to **listed** (this amends #50: the privacy concern goes away
  once the pool is name-only. The owner can still unlist, and `TeamUpdate` gets the toggle).
- The opponent combobox in the lineup creator merges three sources:
  1. listed teams from the directory (`/teams/pool?search=`),
  2. **recent opponents of this team**: distinct `opponent_name` values from its own saved
     lineups (**new** small endpoint `GET /teams/{id}/opponents/recent`). This covers teams that
     never signed up, without polluting the shared directory,
  3. free text, as today. The name is frozen in the snapshot.
- Not now (maybe later): "add this opponent to the shared directory" as member-less directory
  entries. It needs duplicate and moderation handling ("FTC" vs "Ferencváros"), which isn't worth
  it for a handful of users.

---

## 7. Lineup previews
- No backend change for v1: the FE calls the existing generate endpoints, takes the PDF blob and
  renders it with pdf.js. The `attachment` header doesn't matter for `fetch`.
- The PDF is the preview for both formats (it's LibreOffice's rendering of the same DOCX).
  DOCX is a download button. In-browser DOCX renderers get this template's tab stops wrong.
- Saved-lineups list: a preview on **hover (desktop, ~300 ms intent delay) or tap (mobile)**,
  with a spinner, cached per lineup (snapshots never change, so the cache never goes stale).
- Lineup creator: a **Preview** button, opening a side panel on desktop and a full-screen sheet
  on mobile. Not live-as-you-type, because each render runs LibreOffice.
- Later, if it feels slow: a server-side cached thumbnail endpoint (**new**, optional).

---

## 8. UI theme (D11, superseded by D14)

_History: the Polaris theme below was replaced by the Lineup design system (D14, `PLAN-ui-redesign.md`, spec in `frontend/DESIGN.md`); do not follow its instructions._
- **Polaris** (tweakcn): deep teal primary + amber secondary, square corners, Google Sans Flex,
  light and dark. The full spec is in `frontend/DESIGN.md`, kept there as guidance for coding
  agents. Install the tokens with `npx shadcn@latest add @shadcnblocks/theme/polaris` during the
  skeleton issue.
- Components use semantic tokens only (`bg-primary`, `text-muted-foreground`), never raw hex.
  Follow the spec's do's and don'ts: square corners, teal for the one primary action, amber
  for secondary.
- AstroVista was considered and dropped.
- More inspiration if needed: Mobbin, Refero, Page Flows (flows such as onboarding/invites),
  shadcn Blocks, Dribbble/Behance. Drop screenshots in a local folder and point me at it.

---

## 9. Verification (per phase)
- Phase 0: a PR into `develop` runs CI, and a direct push to `main` is rejected. After the move,
  `task test` (100 %), `task lint` and `task test-e2e` pass unchanged.
- Phases 1/3: `task lint`, `task test` (100 %), `task test-e2e`, and `supabase-smoke` on dev.
  Two Google accounts can't see each other's teams. A member sees the owner's roster.
- Phases 2/6: `pnpm lint && pnpm typecheck && pnpm test && pnpm build`. Playwright runs at
  desktop and phone viewports (`task fe:e2e`, #159: production build, network mocked in the browser).
  Throttled/delayed API responses showing skeletons and the wake-up banner are not covered by the
  mocked suite; they were checked by hand against a slow local API (PR #126).
- Phase 4: a push to `develop` deploys both sides. After ≥ 15 min idle, the first page load shows
  the banner, then data. The first PDF finishes under 120 s.
- Phase 6 i18n (#155): switching the language changes all visible text and a reload keeps it; no hard-coded
  user-facing string is left.
- #156 keep-alive: a manual `workflow_dispatch` run succeeds and prints no secret.
- Phase 5: the invite link works end-to-end with a second Google account. Expired/revoked →
  410/404. A non-owner can't invite (403).

---

## 10. Progress log
| Date | What | Refs |
|---|---|---|
| 2026-10-03 | Plan drafted; all decisions D1–D11 agreed. Polaris chosen (spec moved to `frontend/DESIGN.md`), invite expiry 24 h by default. | — |
| 2026-10-03 | `develop` created and made the default branch. Both branches protected; CI, Dependabot and wiki sync retargeted; skills/docs updated. (Done without a separate issue.) | — |
| 2026-10-03 | Backend moved into `backend/` on branch `chore/86-move-backend-into-backend-dir` (`git mv`, Taskfile `dir: backend`, Docker context `backend/`, compose `env_file`, CI `working-directory`, Dependabot `/backend`, docs and skills updated). Merged in PR #87. | #86, #87 |
| 2026-10-04 | Compliance audit (GDPR + OWASP): epic #92 with gap issues #93–#98, compliance sections added to #19/#51/#25/#13, and the `compliance-audit` skill (full + quick per-feature mode) with its compliance gate before Phase 4. Merged in PR #99. | #92, #99 |
| 2026-10-04 | Phase 0 finished: #13, #17, #8, #20, #19, #49, #50, #51 and #39 amended to the plan (decision sections appended), new issues #100 (prod CD from `main`, M2) and #101 (Google OAuth + JWKS on dev, M3), milestones renamed to "M2 – Prod" and "M3 – Dev preview" with the dev-preview issues moved into M3. Repo bookkeeping in PR #103. | #100, #101, #102, #103 |
| 2026-10-04 | Phase 1 planned as 5 PRs: docs tooling (#104), then API surface (#69, #56), input hardening (#53–#55), container + PDF (#70, #71), DB/CI (#60, #68). Decisions: drop `limit=0` (cap 200), unknown `team_id` → 404, RLS/role switch last. PR 0 adds the docs gate, Newcomer Guide and References page. | #104, #105 |
| 2026-10-05 | PR 1 of Phase 1: `GET /health` (+ `?db=1`), `CORS_ORIGINS` allowlist, `max_length` on the one-off request, `limit` capped at 1–200 (`limit=0` dropped), literal `%`/`_` in the pool search. #69 moved to M1. | #69, #56, #106 |
| 2026-10-05 | PR 2 of Phase 1: shared `CleanStr` input types (trim, no control chars, blank optional → `None`), unknown `team_id` → 404 (+ stray `IntegrityError` → 409), source id xor free text, duplicate NSSZ → 422, deterministic list ordering and cap-sorted snapshots on create. | #53, #54, #55, #107 |
| 2026-10-05 | PR 3 of Phase 1: two-stage Dockerfile pinned by digest, non-root `app` user, tini, `/health` HEALTHCHECK, `libreoffice-writer-nogui` (image 1.16 GB → 870 MB, e2e fidelity unchanged); PDF conversions capped by `PDF_MAX_CONCURRENT` (503 + `Retry-After`), process-group kill on timeout, distinct missing-binary/output errors, cwd-independent template path; Dependabot docker ecosystem added (partly covers #73). | #70, #71, #108 |
| 2026-10-05 | PR 4 of Phase 1: `alembic upgrade head` + `alembic check` in CI (SQLite, plus a Postgres 17 service job that also asserts RLS/grants and round-trips the migration); Postgres-only migration enabling RLS everywhere, revoking `anon`/`authenticated`, adding the `lineup_enable_rls` event trigger and the `lineup_app` role; `MIGRATE_DATABASE_URL` in a separate `backend/.env.migrate`; `task migrate:supabase`, `task migrate-check`, `task db:create-app-role`. Applying it to dev Supabase and switching the app to `lineup_app` is left to the owner. | #60, #68, #111 |
| 2026-10-05 | #68 rolled out on the dev Supabase project: migration `8b1f3c2d9a47` applied through the session pooler (the direct host is IPv6-only), `lineup_app` given a password and `backend/.env` pointed at it, `supabase-smoke` passed as `lineup_app` (create, read, generate DOCX, delete). Found on the way: plain `postgresql://` migration URLs failed with `ModuleNotFoundError` (fixed in #115). | #68, #114, #115 |
| 2026-10-05 | Phase 2, PR 1: Vite + React + TypeScript app in `frontend/` (pnpm, Tailwind v4 with the Polaris tokens in light and dark, self-hosted Google Sans Flex, sidebar / bottom-nav shell, React Router, TanStack Query provider), API client generated offline from the backend's OpenAPI spec with a CI freshness check, `task fe:*` targets, a `Frontend` CI job and a Dependabot `npm` entry. Verified in Chromium at desktop and phone sizes. Sub-issues #119–#121 of epic #20. | #119, #20, PR #123 |
| 2026-10-05 | Phase 3, PR 1: `get_current_user_id()` verifies the Supabase JWT (ES256/RS256 only, cached JWKS, `iss`/`aud`/`exp`/`nbf`) and returns the `sub` UUID; 401/503 fail closed; repositories take a required user id; saved-lineup create resolves source ids as the caller; `Auth Setup` wiki page. `POST /lineups` stays public until #96. | #101, #47, #122 |
| 2026-10-05 | Phase 2, PR 2: cold-start-aware data layer: `BackendStatusProvider` polls `/health` on load (`unknown → waking → ready` or `db-paused` or `down`, banner after 1.5 s behind `VITE_COLD_START_NOTICE`), TanStack Query retries only transient failures (1-2-4-8 s backoff, never 4xx or mutations), 60 s / 130 s (PDF) request timeouts, `QueryBoundary` + `Skeleton` for data regions and a `loading` button. Checked in Chromium with a slow, gateway-erroring, db-paused and 404 API. | #120, PR #126 |
| 2026-10-05 | Phase 3, PR 2: `team_members` + `team_invitations` (RLS, grants, interim policy), creator inserted as `owner`, owner columns `NOT NULL` (ownerless dev rows deleted by the migration, not backfilled), `supabase-smoke` skill authenticates through `scripts/smoke_auth.py`. Applying the migration to dev Supabase is left to the owner. | #19, #52, #125 |
| 2026-10-05 | Phase 3, PR 3: the team is the workspace. `players.team_id` and `saved_lineups.team_id` required, `created_by` audit-only, all access through `team_members` (404 for non-members, 403 for non-owner members on owner actions), source ids resolved as the caller, `is_public` toggle + id/name-only pool, `GET /teams/{id}/opponents/recent`, team delete blocked by saved lineups, FE client regenerated. Applying migrations to dev Supabase + smoke test left to the owner. | #49, #48, #50, #127 |
| 2026-10-05 | Phase 2, PR 3: the first screen, a one-off lineup form (React Hook Form + a Zod schema that mirrors the API limits) calling `POST /lineups` and downloading the PDF or DOCX; API 422s are mapped onto the fields, a PDF-wait message appears after 5 s, nothing is persisted client-side. Verified in Chromium against a real container: a 15-player PDF and a DOCX downloaded, with `ő`/`ű` in the file name. Decisions for #20 recorded in `Roadmap-Frontend.md`; Phase 2 is complete. | #121, #20, PR #128 |
| 2026-10-05 | Phase 3, frontend: Google sign-in through `@supabase/supabase-js` (sign-in only, PKCE, publishable key only: a secret key is refused), `AuthProvider` + route guard, the token on every API call except `/health` (a 401 signs out, a 503 shows the retry box, never a sign-in loop), a same-site-only return path, and team onboarding (create a team; invite-link field disabled until #51) with the current team and sign-out in the shell. Unit-tested with a fake auth client; checked in Chromium at phone and desktop sizes against a local backend and the `scripts/smoke_auth.py` stand-in (43 checks: redirect to sign-in, OAuth start URL, onboarding, token header, 401/503 states). The real Google round trip waits for the manual #101 setup. | #129, PR #130 |
| 2026-10-28 | Phase 3 rolled out on the dev Supabase project: migrations `a3d5f7c91e26` and `e5b8c2d41f70` applied through the session pooler (they delete the pre-auth dev rows), `supabase-smoke` passed as `lineup_app` (team, player, saved lineup, DOCX generate, delete), the Google OAuth client and Supabase Google provider set up per `Auth-Setup.md`, and a real Google sign-in tried in the UI (onboarding, team, API calls with the token). | #101, #129, PR #153 |
| 2026-10-28 | Plan amended: i18n added as D12 and the first Phase 6 item (#155), versions and releases as D13 (#17 moved to M3: one repo-wide `vX.Y.Z` tag, a manual `release` workflow instead of semantic-release because commits are `#N - subject`), and the Supabase keep-alive made twice-weekly with its own issue (#156, D8). Backlog issues #157–#164 filed (APM, Claude Code guard rails, Playwright, Schemathesis, mutation testing, PDF load test, dev container, Supabase backup). `CLAUDE.md` turned into a router with path-scoped rules (#154, PR #165) and skills pinned to model aliases (#76, PR #166), both merged. | #154, #155, #156, #17, #76, PR #167 |
| 2026-10-28 | Phase 4: `keepalive.yml` (#156): `SELECT 1` through the Supabase pooler on Mondays and Thursdays (plus `workflow_dispatch`), `psql` from the runner and no third-party actions, accepts the app's asyncpg URL form. The owner still sets the `KEEPALIVE_DATABASE_URL` secret, runs it once by hand and checks two scheduled runs. | #156, PR #168 |
| 2026-10-28 | Phase 4: API hardening (#96): `lineup/security/` with security headers and `no-store` on every response, a 256 KiB body cap (413), an in-house in-memory sliding-window rate limiter (per IP before sign-in, per user after; shared by both generate endpoints; 429 + `Retry-After`), `POST /lineups` requires sign-in, `/docs` off with `ENV=production` (or `DOCS_ENABLED=false`), and `validate_production_config()` (needs a `postgresql+asyncpg` `DATABASE_URL` with `ssl=require`/`verify-full` and `SUPABASE_URL`). The e2e test signs in with a throw-away key (`scripts/e2e_keys.py`, `compose.e2e.yml`). Limiter state is per process: fine for one Fly machine. | #96, PR #171 |
| 2026-10-28 | Phase 6, #155: Hungarian by default, English selectable (react-i18next; `src/i18n/` with `hu.json` + `en.json`). Every existing screen uses `t()`; Zod schemas emit error keys that `Field` translates at render time, `describeError()` and the nav labels are translated, `<html lang>` follows the language, and the language switch is in the account panel and on the sign-in page. The choice is the only new storage (`lineup-lang`, strictly necessary preference). `eslint-plugin-i18next` (`no-literal-string`) fails the build on a hard-coded string. Checked in Chromium at 360 px and 1280 px. Known gap: server 422 sentences stay English. | #155, PR #172 |
| 2026-10-28 | Follow-up to #171 and #172: `supabase-smoke` passed against dev Supabase with the new code (team, player, saved lineup, DOCX generate with `no-store`/HSTS/nosniff headers, no-token `POST /lineups` → 401, delete; run on a spare port because the dev container held `:8000`); the browser-storage entries and rate-limit counters to disclose were posted on #94; #156 keep-alive verified with a manual run. The Fly app (#13) and Cloudflare Pages deploy are done separately by the owner. | #94, #96, #155, #156 |
| 2026-10-29 | Phase 4, #13 (config part): `backend/fly.toml` for the dev app `lineup-dev-lb` (region `ams`, the closest EU region to Supabase `eu-west-1`; scale to zero; 1 GB; `/health` check; `ENV=production`, `CLIENT_IP_HEADER`, `PDF_MAX_CONCURRENT=1` in `[env]`, secrets via `fly secrets`), a guard test (`tests/test_fly_config.py`) and the `Fly Setup` wiki page. The owner has not used Fly before, so the account, app creation, DPA, secrets and first deploy are manual steps in that page. | #13, PR #174 |
| 2026-10-30 | Phase 4, #13: the owner created and deployed the Fly app `lineup-dev-lb` (name `lineup-dev` was taken; `-lb` = owner's initials). The first deploy made two machines (Fly's HA default); scaled to one with `fly scale count 1`, and `--ha=false` is now documented everywhere (the in-memory rate limiter needs exactly one). Checked live: `/health` and `/health?db=1` 200, `/docs` 404, `POST /lineups` without a token 401, security headers present, cold start of `/health` about 5 s. Still open on #13: DPA in the Fly Trust Center (not on the public legal page), billing alerts, PDF cold-start test. New issue #175 for the Cloudflare Pages deploy (sub-issue of #20, blocks #8). | #13, #175, PR #174 |
| 2026-10-30 | Correction to #13: Fly has no billing alerts or spending limit (its docs say so), and a new account runs on a no-card trial of up to 2 h of machine runtime or 7 days. Runbook gets a *Trial and billing* section; the PLAN item is reworded to "add credits or a card before the trial ends, check the bill". | #13 |
| 2026-10-30 | Phase 4, #175 (repo part): compliance quick-check (G9, G10, G14, S5, S6, S7, S10, S11, S13), baseline security headers in `frontend/public/_headers` with a guard test, no `404.html` so Pages keeps SPA mode, the `Pages Setup` wiki page (project settings, build variables, allow-lists, Web Analytics off, why PR previews cannot sign in) and the docs that point to it. The Cloudflare account, DPA, project, secrets and the cold-start test are manual steps for the owner. | #175, PR #177 |
| 2026-10-30 | Phase 4, #175 done: the owner created the Pages project (production branch `develop`, root `frontend`, React (Vite) preset with the `pnpm` build command; the dashboard first offered the Workers flow, the Pages one is behind a link on the Create page), set the five public build variables, `CORS_ORIGINS` on Fly and the Supabase Site URL/redirects for `https://lineup-kfi.pages.dev`. Verified: the `_headers` set is served, `/some/deep/link` returns the app, the CORS preflight echoes the origin, Google sign-in works and the cold-start PDF test (after 15 min idle) passed and was fast. | #175, #13, PR #178 |
| 2026-10-31 | Scope triage for a small, known-user project: every open issue labelled `plan:keep`, `plan:keep-cheap`, `plan:defer` or `plan:drop`. Closed as completed: #21 (RLS shipped in #68), #40 (team-scoped access shipped). Closed as not planned: #100, #18, #161, #163 (no prod environment; no mutation testing; no dev container). Status comments added where work is partly done (#38, #62, #64, #73, #76, #77, #78, #79, #158). Decision D1 and the branching docs amended: one dev/test environment, no prod. The users are not from one household, so GDPR still applies. Deferred issues and the remaining prod issues moved to the new milestone "Mx – Parked", and "M2 – Prod" was closed; #92 moved to M3. New sibling of #18: #179 (Supabase web client as a dev admin tool, a step-by-step guide in `documentation/`). The AI setup work (#157) moves to the private `ai-common` repo (first scaffold: hooks from `dev-config`, templates, the `new-issue` skill, a draft `convention-reviewer` agent and docs). | #21, #40, #100, #18, #161, #163, #157, #179, PR #180 |
| 2026-10-31 | Phase 4, #8 (workflow part): `deploy-dev.yml` runs on a push to `develop` that touches `backend/**` (or by hand): `alembic upgrade head` with the session-pooler `MIGRATE_DATABASE_URL` secret, `flyctl deploy --ha=false` with an app-scoped `FLY_API_TOKEN`, then 18 tries of `/health?db=1`. Runs queue and are never cancelled; the one third-party action is SHA-pinned; `tests/test_deploy_workflow.py` guards it. The Pages deploy stays with the Pages Git integration (no Cloudflare token in GitHub). The owner sets the two secrets and runs it once by hand. Fly billing was handled by the owner (card added). The compliance gate (#94, #97, #93) is moved to the very end, after the features, at the owner's request. | #8, PR #184 |
| 2026-10-31 | Phase 4, #8 done: the owner set the `FLY_API_TOKEN` and `MIGRATE_DATABASE_URL` secrets (there was no local `backend/.env.migrate`, so the URL was built from the Supabase dashboard's session-pooler string) and ran *Deploy dev* by hand: green (migrate, `flyctl deploy --ha=false`, `/health?db=1` 200), one Fly machine with its check passing. The push-triggered run right after the merge of #184 failed at the first step as expected, because the secrets did not exist yet. | #8 |
| 2026-10-31 | Phase 5, #51 (backend): invitation links and members. Owners create, list and revoke multi-use links (2/24/72 h) under `/teams/{id}/invitations`; `GET /invitations/{code}` is the one public route that takes a code (team name, inviter's display name, expiry); `POST /invitations/{code}/accept` joins as a member (idempotent, 404/410). `GET /teams/{id}/members`, remove / leave (the last owner gets 409) and `POST /teams/{id}/transfer-ownership`. Codes are `token_urlsafe(32)` with only the SHA-256 stored; uvicorn runs with `--no-access-log` because the code is a URL path segment; the inviter's name is snapshotted from the token (`invited_by_name`, migration `b7d2e9a41c53`) and links are purged a week after expiry; `APP_BASE_URL` builds the url. The every-route-needs-a-token test was silently collecting nothing on FastAPI 0.162 (`app.routes` holds `_IncludedRouter`) and now reads `app.openapi()`. The FE members page and `/join/:code` are the next Phase 5 item; run `supabase-smoke` once the migration is on dev. | #51, PR #186 |
| 2026-10-31 | Phase 5, #189 (frontend): the Team page (`/members`: members as "You" / "Member N", owner tools to remove, hand over, create/copy/share/revoke invite links, everyone can leave) and the public `/join/:code` page (preview before sign-in, survives the Google round trip, joins only on a second button; the remembered path holding the code is cleared once signed in, after joining and on sign-out). The onboarding invite field works. Checked in Chromium at phone and desktop sizes against the real API on throwaway SQLite plus the fake Supabase Auth. Found and fixed: `AuthProvider` clearing the query cache made the preview request go out twice. Around it: `supabase-smoke` now covers the invitation endpoints and passed on dev (PR #191, migration `b7d2e9a41c53` confirmed there); `setup-flyctl` moved to a Node 24 release (#192, PR #193, deploy verified); follow-up #190 runs the smoke test after every dev deploy. | #189, #51, #190, #191, #192, #193, PR #194 |
| 2026-10-31 | Compliance gate, #94: the GDPR documentation pack is written as five wiki pages: Privacy and Security (data inventory of every model column, browser storage, in-memory counters, retention, sub-processors and regions, backups, open gaps, by-hand request handling, pre-invite checklist), Privacy Notice (HU + EN, Art. 13 and the Art. 14 club template), Terms and Processor Agreement, Compliance Records (Art. 30 x2, LIA, DPIA screening) and Breach Runbook. Operator details are `[…]` placeholders for the owner; the issue stays open until they are filled and the ⚖ items are read. | #94, PR #196 |
| 2026-10-31 | Phase 4, #190: `scripts/smoke_live.py` is the single definition of the live smoke test (team, player, saved lineup, DOCX, invitation flow; always cleans up; sweeps `smoke-<time>` teams older than an hour), and `deploy-dev.yml` gets a `smoke` job that runs it as `lineup_app` after a green deploy, on pushes to `develop` only. `smoke_auth.py` now signs two stable users so the sweep can find leftovers; all actions in the workflow are SHA-pinned. Checked locally against a throw-away SQLite API (21 steps); the real Supabase run waits for the owner's `SMOKE_DATABASE_URL` secret. | #190, PR #195 |
| 2026-10-31 | Phase 6, #197 (frontend): the Roster page. `PlayersCard` (list, add, edit in place, delete with a confirm; any member, a hint says saved lineups keep their frozen copy), `TeamSettingsCard` (owners only: rename and directory listing through `PUT /teams/{id}`), `DirectoryCard` (debounced search over `GET /teams/pool`, names only) and a `useDebouncedValue` hook. No backend change, no new storage or fields (nothing to add to the #94 inventory). Built as three parallel slices and checked with lint, format, typecheck, 356 unit tests, the build and the API-client freshness check, then tried in headless Chromium against a throw-away local API with the fake Supabase Auth (24 checks at desktop and phone size: add, edit, delete, reload, validation, rename and unlist, directory search, Hungarian; no console errors, no request outside the local stack, only the auth session and `lineup-lang` in storage), and the member permissions (manage players yes, rename team 403) checked through the API with a second user. | #197, #20, PR #198 |
| 2026-10-31 | Phase 6, #203 (frontend): the lineup creator. `/` builds a lineup for the current team: each slot is a roster player (name and NSSZ copied in and locked, one use per player) or typed-in text; the opponent field is a native combobox over the listed directory, the team's recent opponents and free text (a listed name keeps its id); **Preview** runs the stateless `POST /lineups` and draws the PDF with pdf.js (lazy chunk, bundled same-origin worker, side panel on desktop and full-screen sheet on a phone, the `Blob` is dropped on close); **Save** uses `POST /lineups/saved` and then offers PDF/DOCX downloads. The one-off form stays as "Quick sheet". Backend: `POST /lineups` now takes the doctor, assistant coach, team leader and ball thrower as optional (like saved lineups). "Clone to new match" passes only a lineup id in the router state, and the page fetches the lineup, so no names reach the history. Built in parallel: the opponent combobox and the Saved page (#204, PR #206) were separate forks, and #190 was verified at the same time (PR #205). 437 unit tests at 100 % coverage. | #203, #204, #190, PR #207 |
| 2026-10-31 | Phase 4, #190 done: the owner set the `SMOKE_DATABASE_URL` Actions secret and the manual *Deploy dev* run on `develop` (run 41233261200) was green end to end: migrate, `flyctl deploy --ha=false`, `/health?db=1`, then the `smoke` job (`scripts/smoke_live.py` as `lineup_app` against the dev Supabase project, 45 s). From now on every backend push to `develop` is smoke-tested after the deploy. | #190, PR #205 |
| 2026-10-31 | Phase 6, #204 (frontend): the Saved page. `SavedLineups` lists the current team's saved lineups newest first; each row previews its PDF (shared `PdfViewer`/`PreviewPanel` from #203, loaded on tap or after a 300 ms hover intent, cached in memory with `staleTime: Infinity`), downloads PDF/DOCX, clones into the creator (only the id travels, as router state `cloneFromId`; the Lineup page fetches the lineup, so no names or NSSZ numbers end up in the tab history) and deletes with a confirm; a 404 says the lineup is gone and reloads. Keys under `["saved", userId, teamId]` so the creator can refresh the list after saving. `ComingSoon` removed. Lint, format, typecheck, build and 411 unit tests at 100 % coverage; no browser check yet. Stacked on #203's branch. | #204, #203, PR #206 |
| 2026-10-31 | Phase 6, #204 (follow-ups): the Saved row whose preview is open now has a visible highlight (left bar in the primary colour plus the accent background; `aria-current` was already set), and generated files get a tidy name: `rajtlista_<team>_<date>.<ext>` with spaces in the team as `_` and the free-text date's dots and spaces as `-` (`2024. 12. 21.` becomes `2024-12-21`, no more `..` before the extension). The printed sheet keeps the date as typed. Backend `download_filename()` with tests; 890 backend and 466 frontend tests at 100 % coverage. | #204 |
| 2026-10-31 | Phase 6, mobile polish (#159): Playwright browser tests (`task fe:e2e`) drive the production build in Chromium at a phone (360x740, touch) and a desktop size with the API and Supabase mocked in the browser (no backend, no login), checking every screen in the light and dark theme for sideways scroll and axe violations, plus sign-in, onboarding, the creator preview and the Saved highlight; a report-only CI job. They found and I fixed: the accessible names of the language switch, "Clone" and "Make owner" did not start with their visible text (WCAG 2.5.3), the creator's roster picker was cut off beside the cap number on a phone (the player row now stacks), text fields were 14 px (iOS zooms on focus; now 16 px on phones) and buttons were 32-40 px (now 44 px on touch screens). Also safe-area padding, `viewport-fit=cover`, a web-app manifest with icons and an apple-touch-icon so the app can be added to the home screen (no service worker: no personal data cached offline). 470 unit tests at 100 % coverage, 42 browser tests (phone and desktop, English and Hungarian, with the experimental axe label-in-name rule on: it also caught Hungarian names such as "Kovács Anna törlése" that did not start with the visible "Törlés"). | #159, PR #209 |
| 2026-10-31 | Dependabot and Trivy clean-up, then #17: PR #210 moved the image to `python:3.14-slim` (3.15 has no wheels for lxml, pydantic-core and four more packages) and removed pip from the runtime stage, which cleared the 13 Trivy code-scanning alerts (all pip's vendored urllib3/certifi/msgpack/setuptools); PR #211 upgraded ruff to 0.17 and fixed its findings (#62). #17 (PR #212): `task release:bump`, `scripts/bump_version.py`, the manual `release.yml` (tag + GitHub Release + migrations list), `lineup/version.py` as the API's single source, `tests/test_versioning.py`; the baseline `v0.1.0` is cut by running the workflow after the merge. |
| 2026-10-31 | #159 follow-up: browser tests for `/join/:code` (public preview that joins nobody, the explicit second click, expired and unknown links, Hungarian axe pass) and the 404 page, with the invitation routes added to `e2e/fixtures.ts` (56 browser tests in all). `CLAUDE.md` now records that work based on a pre-agreed issue may be committed, pushed, PR'd and merged without asking again, and that subagents are used where reasonable. | #159, PR #219 |
