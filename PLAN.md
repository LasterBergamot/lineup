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

Production (prod Supabase project, prod CD from `main`, releases, RLS, observability) comes
**after** the dev preview, as milestone M2.

**Ordering constraint:** a public URL must not exist before real auth. Today
`get_current_user_id()` returns `None`, so everyone sees and edits everything. Auth comes
before the public deploy, and the public deploy comes before inviting anyone.

---

## 2. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | **Two environments only: dev + prod.** No separate test environment. | Decided |
| D2 | **Branches: `develop` → dev, `main` → prod.** Feature branches PR into `develop` (the default branch). A release is a `develop` → `main` PR, which later tags a version (#17). Hotfixes branch off `main` and are merged back into `develop`. | Decided |
| D3 | **Monorepo with `backend/` and `frontend/` at the root** (see §4). | Decided |
| D4 | **FE stack:** React + TypeScript + Vite, Tailwind, shadcn/ui, TanStack Query, React Router, React Hook Form + Zod, client generated from `/openapi.json` (openapi-typescript + openapi-fetch), pdf.js for previews, Vitest + Playwright. | Decided |
| D5 | **Hosting:** API on Fly.io (scale to zero), FE on Cloudflare Pages. | Decided |
| D6 | **Auth:** Google OAuth through Supabase Auth. The FE uses `@supabase/supabase-js` for sign-in only; all data goes through FastAPI. The API validates the JWT against the project's JWKS. | Decided |
| D7 | **Dev behaves like prod** (same sign-in and invite flow). Access to dev is limited by keeping the Google OAuth consent screen in **Testing** mode, with a list of test users (see §6.4). | Decided |
| D8 | **Supabase free-tier pause:** a weekly GitHub Actions cron calls `/health?db=1`. The FE detects a paused DB and says so (see §5.3). | Decided |
| D9 | **Milestones:** **"M3 – Dev preview"** holds the dev-preview work (auth, teams and invitations, UI, dev deployment); **"M2 – Prod"** is the prod milestone. Phase 1 issues stay in M1, since Phase 1 is a subset of it. | Decided |
| D10 | **Team/ownership model:** teams as workspaces, owner + member roles, multi-use invite links, name-only public opponent directory, invite links that expire after 24 h by default (see §6). | Decided |
| D11 | **UI theme: Polaris** (tweakcn, shadcn tokens). Its spec lives in `frontend/DESIGN.md`. AstroVista was dropped. | Decided |

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
- [ ] #68 least-privilege DB role + RLS as migrations. Migration, `task migrate:supabase` and `task db:create-app-role` landed in PR #111; **still to do by hand on dev Supabase:** apply the migration, run `db:create-app-role`, run `supabase-smoke` as `lineup_app`, then close #68.
- [x] #60 Alembic migrations in CI (CD will run them) (PR #111)

### Phase 2 — Frontend skeleton (can run in parallel with Phase 3)
- [ ] **new** FE skeleton + tooling + CI: Vite app in `frontend/`, Tailwind + shadcn with the
      Polaris theme (D11, light + dark), and an app shell (sidebar on desktop, bottom nav on mobile). Also the
      generated API client (a CI check fails if it's stale), `task fe:*` targets, and a CI job
      (lint, typecheck, test, build).
- [ ] **new** Cold-start-aware data layer (§5): skeleton loaders, a wake-up banner, retry policy.
- [ ] First screen: a one-off lineup form calling `POST /lineups` against the local container.
      This meets #20's acceptance.

### Phase 3 — Real auth on dev
- [ ] #101 (split from #39) Google provider on the dev Supabase project. `get_current_user_id()`
      validates the JWT via JWKS and returns `sub`.
- [ ] #47 fail closed (401 without a valid token)
- [ ] #19 `team_members` / `team_invitations` schema (as amended by §6)
- [ ] #49 team-scoped access for players and saved lineups
- [ ] #48 IDOR on saved-lineup create
- [ ] #50 `is_public` semantics (as amended by §6)
- [ ] #52 NOT NULL owner/user ids. On dev the existing rows can simply be wiped instead of
      backfilled.
- [ ] **new** FE: sign-in page, token on every call, onboarding ("no team yet → create one or
      paste an invite link").
- [ ] Run the `supabase-smoke` skill after the model changes.

### Phase 4 — Dev deployment + CD
**Compliance gate (#92):** before anyone outside the team gets access to dev, the following
must be done:
- #94 GDPR documentation pack
- #93 Sentry PII scrubbing (required before any `SENTRY_DSN` is set)
- #97 frontend privacy/security baseline

#96 (API hardening) should land with the public deploy.
- [ ] #13 Fly.io app `lineup-dev`: `auto_stop_machines`, `min_machines_running = 0`, ~1 GB RAM
      for LibreOffice. Secrets via `fly secrets`: pooler `DATABASE_URL`, `ENV=production`,
      Supabase JWKS URL, `CORS_ORIGINS`.
- [ ] **new** FE deploy to Cloudflare Pages: `VITE_API_URL`, `VITE_SUPABASE_URL`,
      `VITE_SUPABASE_ANON_KEY`, and `VITE_COLD_START_NOTICE=true`. Every PR gets a preview URL.
- [ ] #8 CD workflow on push to `develop`: Alembic `upgrade head` (session-pooler URL from GitHub
      secrets), then `flyctl deploy`, then poll `/health?db=1` with a cold-start-tolerant retry,
      then the Pages deploy. If the health check fails, Fly keeps the previous release.
- [ ] **new** Weekly keep-alive cron (D8, §5.3)
- [ ] Billing/usage alerts on Fly.io and Supabase (#13)

### Phase 5 — Invitations
- [ ] #51 endpoints, in the link-based form of §6
- [ ] **new** FE: team members page, "Invite" button (copy link / mobile share sheet),
      `/join/:code` page that survives the Google sign-in round trip.

### Phase 6 — Feature-complete UI
- [ ] **new** Roster management (teams, players, opponent directory search)
- [ ] **new** Lineup creator: roster pick or free text, cap-number validation, opponent combobox
      (directory + recent opponents + free text), Preview panel.
- [ ] **new** Saved lineups: list, hover/tap preview, generate PDF/DOCX, delete,
      "Clone to new match".
- [ ] Mobile polish: Playwright at a phone viewport; optional web-app manifest ("Add to home screen").

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
  inactivity. The weekly cron should prevent it, but GitHub disables scheduled workflows in
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
- The stateless one-off `POST /lineups` stays as it is.

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

## 8. UI theme (D11)
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
  desktop and phone viewports against the local container. Throttled/delayed API responses show
  skeletons and the wake-up banner.
- Phase 4: a push to `develop` deploys both sides. After ≥ 15 min idle, the first page load shows
  the banner, then data. The first PDF finishes under 120 s.
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
