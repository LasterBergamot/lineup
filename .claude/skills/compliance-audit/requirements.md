# Lineup compliance requirements

**Last reviewed:** 2026-10-04 · **Tracking epic:** #92

This is the checklist that `compliance-audit` (full and quick modes) checks the repo against.
It turns GDPR, the Hungarian rules and the OWASP baseline into concrete, checkable items for
this app. It is not legal advice. Items marked ⚖ are worth a lawyer's look once before prod.

**What we process.**
- Players: full name, NSSZ number (federation registration id), cap number, team. Some players are minors.
- Staff: names of the coach, doctor, assistant coach, team leader and ball thrower.
- User accounts: Google email and `sub`, plus team memberships and invitations.
- The generated PDF/DOCX files contain the player and staff data.

**Roles.** Several clubs use the app. Each club is the **controller** of its roster and lineup
data. We are the club's **processor**, and the **controller** for user accounts.

**Processors.** Supabase (DB + Auth), Fly.io (API), Cloudflare Pages (FE), Sentry (errors).
Google acts as an independent controller for sign-in.

Each item lists:
- **Level:** MUST (legal duty or strong baseline) or SHOULD.
- **Check:** where to look in this repo.
- **Source:** the authority it comes from.

## GDPR

| ID | Level | Requirement | Check | Source |
|---|---|---|---|---|
| G1 | MUST | The household exemption doesn't apply. Clubs are organisations, and Recital 18 excludes whoever provides the tools. GDPR applies in full. | n/a (premise) | [GDPR Recital 18](https://eur-lex.europa.eu/eli/reg/2016/679/oj), CJEU C-212/13 |
| G2 | MUST ⚖ | Lawful basis is Art. 6(1)(f) legitimate interest (organising matches and registration), backed by a written 3-step LIA in which children's interests carry extra weight. Don't use consent: it can be withdrawn and is hard to obtain for minors. | `documentation/Privacy-and-Security.md` has the LIA | [EDPB Guidelines 1/2024](https://www.edpb.europa.eu/our-work-tools/documents/public-consultations/2024/guidelines-12024-processing-personal-data-based_en) |
| G3 | MUST | Art. 8 (child consent) doesn't apply, because adults enter the data and players never sign in. The ToS bar accounts for under-16s, and minors' data is treated as higher-risk. | ToS text; no age/DOB field unless justified | GDPR Art. 8; HU age 16 |
| G4 | MUST | Minimisation: only name, NSSZ, cap number and team for players, and names only for staff. No DOB, photos, contact details or health data. The "doctor" field is a name and never holds medical notes. | `backend/lineup/db/models.py`, `*/schemas.py`: every new column is justified in the data inventory | GDPR Art. 5(1)(c) |
| G5 | MUST | Storage limitation: written retention rules (removed players, old lineups, expired invites, inactive accounts) that are actually enforced. Generated files are made on demand and never stored. | retention section in the inventory; purge job/tests; no file persistence | GDPR Art. 5(1)(e) |
| G6 | MUST | Data subject rights exist as features: export (Art. 15/20), edit (16), erasure that also reaches saved-lineup snapshots (17), account self-deletion including the Supabase auth user, and a contact address. As processor, we help clubs answer requests (Art. 28(3)(e)). | export/erasure endpoints + tests; PII-tag coverage test (#95) | GDPR Arts. 15–20, 28(3)(e) |
| G7 | MUST ⚖ | Privacy notices in Hungarian and English: Art. 13 for account holders, and an Art. 14 template clubs pass to players, staff and parents (the data doesn't come from the players themselves). | notice source in repo; FE links it on the sign-in page and in the footer | GDPR Arts. 13, 14 |
| G8 | MUST | Art. 30 records of processing, both as controller and as processor. The under-250-employees exemption doesn't apply because the processing isn't occasional. | records committed | GDPR Art. 30(1), (2), (5) |
| G9 | MUST ⚖ | DPAs accepted with every processor and listed as sub-processors. Clubs get ToS with an Art. 28 processor agreement. | sub-processor list in the inventory | [Supabase DPA](https://supabase.com/legal/dpa), [Sentry DPA](https://sentry.io/legal/dpa/), [Cloudflare DPA](https://www.cloudflare.com/cloudflare-customer-dpa/), [Fly.io legal](https://fly.io/legal) |
| G10 | MUST | International transfers rely on the EU–US DPF, with SCCs as the fallback (the DPF challenge T-553/23 was dismissed in Sep 2025, but an appeal is possible). Pin EU regions: Supabase, Fly `fra`/`ams`, Sentry EU. | region of each project recorded; `fly.toml` `primary_region` | [General Court T-553/23](https://curia.europa.eu/jcms/upload/docs/application/pdf/2025-09/cp250106en.pdf) |
| G11 | MUST | Breaches: keep an internal log of every incident and notify NAIH within 72 h unless the breach is unlikely to cause risk. As processor, notify clubs without undue delay. Tell data subjects if the risk is high. | breach runbook committed | GDPR Arts. 33, 34; [NAIH reporting](https://naih.hu/adatvedelmi-incidensbejelento-rendszer) |
| G12 | SHOULD | DPIA screening note. A full DPIA is probably not required (small scale, no profiling, no special categories), but minors are a risk factor, so write down the reasoning. | screening note committed | GDPR Art. 35; [EDPB DPIA guidelines](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-data-protection-impact-assessment-dpia-and-determining_en) |
| G13 | MUST | Privacy by design and by default: team-scoped access, teams private or name-only listed, short invite expiry, nothing shown publicly beyond team names, no PII in logs or Sentry. | `is_public` default (#50); `/teams/pool` exposes `id` + `name` only | GDPR Art. 25 |
| G14 | MUST | ePrivacy: localStorage counts as terminal storage. The Supabase auth token is strictly necessary, so it needs no consent but is disclosed in the notice. Analytics, trackers, Session Replay and third-party fonts or CDNs need consent or must be avoided. Self-host fonts (Google Fonts sends visitors' IPs to Google). | `frontend/` network requests, `index.html` font links | [EDPB Guidelines 2/2023](https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-22023-technical-scope-art-53-eprivacy-directive_en) |

## Security (OWASP Top 10:2025, ASVS 5.0 L1/L2, API Security Top 10 2023)

| ID | Level | Requirement | Check | Source |
|---|---|---|---|---|
| S1 | MUST | JWTs are validated against the Supabase JWKS with asymmetric keys (ES256/RS256) and an allowlist of algorithms (never `none` or HS*). Check `iss`, `aud=authenticated`, `exp`/`nbf` with small clock skew. Cache the JWKS and refetch on an unknown `kid`. `sub` is the identity. | `backend/lineup/auth/dependencies.py` | ASVS V9, V10; [Supabase signing keys](https://supabase.com/docs/guides/auth/signing-keys) |
| S2 | MUST | Every id the caller sends (team, player, lineup, invite, `source_*_id`) is checked server-side against the caller's team membership and role (BOLA/IDOR). Tests try to reach another team's data. | `*/service.py`, `*/repository.py` — no `user_id=None` lookups | OWASP A01; API1/API3/API5 |
| S3 | MUST | Fail closed: a missing or invalid identity → 401. A repository filter is never skipped because the id is `None`. | `if owner_id is not None:` patterns (#47) | OWASP A01, A07 |
| S4 | MUST | Invite codes have ≥ 128 bits of randomness (`secrets.token_urlsafe(32)`), only a SHA-256 hash is stored, comparison is constant-time, and codes expire, can be revoked and are bound to a role. They never appear in logs or Referer. | `team_invitations` model/migration (#19, #51) | ASVS V6/V7 |
| S5 | MUST | The Supabase secret/service-role key stays server-side only; only the publishable key may reach the SPA. RLS is on for every `public` table (deny-all if only the backend touches them) or the Data API is off. The app connects with a least-privilege role. | `frontend/.env.example`, migrations (#21, #68) | [Supabase API keys](https://supabase.com/docs/guides/api/api-keys) |
| S6 | MUST | Secrets live only in platform stores (Fly secrets, Cloudflare env, GitHub secrets). Nothing in git; push protection is on; there is a rotation path. Tasks never echo credentials. | `git log -S`, `.gitignore`, `.dockerignore`, `Taskfile.yml`, secret-scanning alerts | OWASP A02 |
| S7 | MUST | TLS everywhere: the DB connection enforces TLS (`ssl=require`, ideally `verify-full` with the Supabase CA), and HSTS is set on the FE and API. | `backend/lineup/db/engine.py`, prod config check (#96) | ASVS V12 |
| S8 | MUST | Logs contain no PII or secrets (names, NSSZ, tokens, Authorization headers, invite codes). Log ids and request ids instead. Authn/authz failures are logged. | `logger.*`/`print` calls; #74 | OWASP A09; ASVS V16 |
| S9 | MUST | Sentry: `send_default_pii=False`, `max_request_body_size="never"`, `include_local_variables=False`, a `before_send` denylist scrubber, EU region, server-side and IP scrubbing. The browser SDK follows the same rules and runs without Replay. | `backend/app.py` init + its tests (#93) | [Sentry sensitive data](https://docs.sentry.io/platforms/python/data-management/sensitive-data/) |
| S10 | MUST | Security headers: a strict CSP (`default-src 'self'`, `connect-src` limited to the API, Supabase and Sentry, `frame-ancestors 'none'`), HSTS, `nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`. API responses carrying PII and generated files are sent with `Cache-Control: no-store`. | `frontend/public/_headers`, API middleware (#96, #97) | OWASP A02; ASVS V3 |
| S11 | MUST | CORS uses an explicit origin allowlist from env: no `*` combined with credentials, and only the methods and headers in use. | `CORSMiddleware` config (#56) | ASVS V3 |
| S12 | SHOULD | Rate limits per IP and per user, tightest on document generation and invite preview/accept. Request bodies have a size cap, every string has a `max_length`, list parameters have upper bounds, and conversions are timed out and capped in concurrency. | schemas `max_length`, limiter (#96), `limit` bounds (#56) | API4 2023 |
| S13 | MUST | Supply chain: Dependabot for every ecosystem, `pip-audit`/`npm audit`, a Trivy image scan, CodeQL, actions pinned to a SHA, base images pinned to a digest, a non-root container, frozen lockfiles. | `.github/**`, `backend/Dockerfile` (#61, #70, #73, #98) | OWASP A03 |
| S14 | MUST | Errors: clients get generic 4xx/5xx bodies with no stack traces, internal paths or other users' ids. Probing for existence returns 404, not 403. | `HTTPException(detail=…)` texts | OWASP A10 |
| S15 | SHOULD | Backups: know what the Supabase tier backs up and for how long, test a restore once, and disclose that erased data survives in backups until they expire. | inventory backup section (#94) | GDPR Art. 32(1)(c) |

## Hungary

| ID | Level | Requirement | Source |
|---|---|---|---|
| H1 | MUST | NAIH is the supervisory authority under Infotv. (Act CXII of 2011). Complaints and breach reports go to NAIH. | [naih.hu](https://naih.hu/), [recommendations](https://naih.hu/adatvedelmi-ajanlasok) |
| H2 | MUST | The notices are in Hungarian, give the controller's contact details and name NAIH and the courts as remedies. | Infotv.; GDPR Art. 13(2)(d) |
| H3 | SHOULD | Minors' rights: for children under 14, parents act; from 14, the minor acts with the parent (Ptk. 2:10–2:12). Requests from either are accepted. | Ptk. |
| H4 | SHOULD ⚖ | Check whether the Sport Act (2004. évi I.) or the MVLSZ rules on NSSZ registration support Art. 6(1)(c) for registration data. | — |

## Quick-mode triggers

The triggers map a change to the requirement IDs it touches. Quick mode (`SKILL.md` §Q) only
checks the IDs a change triggers.

| The change… | Check |
|---|---|
| adds or changes a field that holds personal data (model, schema, DTO, template) | G4, G5, G6, G13, S8, S9; data inventory + PII tag |
| adds an endpoint, or a path/body/query param that carries an id | S2, S3, S12, S14 |
| touches auth, sessions, tokens or invites | S1, S3, S4, S6, S8 |
| adds an external service, SDK, region or processor | G9, G10, G14, S5, S6 |
| touches logging, Sentry or error handling | S8, S9, S14 |
| generates, stores or exports files or data | G5, G6, S10 (`no-store`) |
| touches FE storage, headers, fonts or third-party assets | G14, S10, S11 |
| touches CI, Docker, dependencies or secrets | S6, S13 |
| deletes or anonymises data, or adds retention | G5, G6, S15 |

## Refreshing this file

On every full audit, re-verify:
- the OWASP Top 10, ASVS and API Top 10 editions;
- the status of the DPF challenge;
- that the processor DPA and sub-processor URLs still resolve;
- the Supabase key and signing-key guidance;
- the Sentry SDK options (`send_default_pii` is being replaced by `data_collection`).

Then update **Last reviewed**.
