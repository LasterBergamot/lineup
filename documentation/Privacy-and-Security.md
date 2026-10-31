# Privacy and Security

This page is the single source for how Lineup handles personal data: who is responsible for what,
which data we hold and why, how long we keep it, who else touches it, and what is still missing.
The notices, the processor terms, the records of processing and the breach runbook are built from
it; if a fact changes, change it **here first**:

- [[Privacy Notice]] (Hungarian and English): what we tell account holders (Art. 13) and the template
  clubs pass to players, staff and parents (Art. 14)
- [[Terms and Processor Agreement]]: the terms of use and the Art. 28(3) agreement with clubs
- [[Compliance Records]]: Art. 30 records, the legitimate-interest assessment and the DPIA screening
- [[Breach Runbook]]: what to do in the first 72 hours

> **This is engineering documentation, not legal advice.** Points marked ⚖ are choices a lawyer
> should confirm once before anyone outside the team is invited. The requirement IDs (G1–G14,
> S1–S15, H1–H4) refer to `.claude/skills/compliance-audit/requirements.md`, tracked in epic #92.

## 1. Who is who

| Role | Who | For what |
|---|---|---|
| **Controller** of the rosters and lineups | Each **club** that uses Lineup | Players, staff, lineups. The club decides to put the data in and why |
| **Processor** | The Lineup operator | Stores and processes that data on the club's behalf, only to run the service (Art. 28) |
| **Controller** of user accounts | The Lineup operator | Sign-in, team membership, invitations |
| **Independent controller** | Google | The Google account used to sign in |
| **Sub-processors** | Supabase, Fly.io, Cloudflare (Sentry later) | Section 5 |

The household exemption does **not** apply: clubs are organisations and Recital 18 excludes
whoever provides the tools (G1).

**Facts the operator must fill in before inviting anyone** (they appear in the notices and terms as
`[…]` placeholders; the repo is public, so use a role-based mailbox, not a private address):

| Placeholder | Meaning | Status |
|---|---|---|
| `[OPERATOR NAME]` | Legal name of the person or entity operating Lineup | to fill in |
| `[OPERATOR ADDRESS]` | Postal address (Art. 13(1)(a)) | to fill in |
| `[PRIVACY E-MAIL]` | Contact for privacy requests and breach reports | to fill in |
| `[APP URL]` | Public address of the web app | to fill in when the dev site is public |

## 2. Personal-data inventory

"Subject" is whose data it is. "Basis" is the GDPR Art. 6 lawful basis (section 6 explains the
choice). Every column of the data model is listed; a new column needs a row here in the same PR (G4).

### 2.1 Stored in our database (Supabase Postgres, `eu-west-1`)

| Data | Table.column | Subject | Purpose | Basis | Retention |
|---|---|---|---|---|---|
| Player name | `players.name`, `lineup_player_snapshots.name` | Players (some minors), entered by the club | Fill the lineup sheet | Art. 6(1)(f) (club's legitimate interest; ⚖ H4 may allow 6(1)(c)) | Until the club deletes the player; snapshots until the saved lineup or its team is deleted |
| NSSZ number (federation registration id) | `players.nssz_number`, `lineup_player_snapshots.nssz_number` | Players | Identify the player on the official sheet | as above | as above |
| Cap number | `lineup_player_snapshots.cap_number` | Players | Appear on the sheet | as above | with the saved lineup |
| Staff names (coach, doctor, assistant coach, team leader, ball thrower) | `saved_lineups.coach`, `.doctor`, `.assistant_coach`, `.team_leader`, `.ball_thrower` | Club staff | Appear on the sheet. The "doctor" field is a name only, never medical notes | as above | with the saved lineup |
| Team, opponent, match, division, cap colour, date | `teams.name`, `saved_lineups.team_name`, `.opponent_name`, `.match_name`, `.division`, `.cap`, `.date` | Mostly clubs, not people; can identify a team's members | Describe the match | as above | with the saved lineup or team |
| Team visibility | `teams.is_public` | Club | Whether the team name is listed in the opponent directory. Default **listed**; only `id` and `name` are ever exposed | as above | with the team |
| User id (Supabase `sub`, a random UUID) | `team_members.user_id`, `teams.created_by`, `players.created_by`, `saved_lineups.created_by`, `team_invitations.invited_by` | Account holders | Access control (who may see a team) and audit | Art. 6(1)(b)/(f) | Memberships until the person leaves or is removed. The `created_by` audit columns **have no purge yet** (see section 8, #95) |
| Role and join date | `team_members.role`, `.joined_at` | Account holders | Owner / member permissions | Art. 6(1)(b) | with the membership; a team's memberships are deleted with the team |
| Inviter's display name | `team_invitations.invited_by_name` | Account holders | Show "invited by …" on the join page before sign-in | Art. 6(1)(f) | Link deleted 7 days after it expires (enforced whenever an owner creates or lists links) |
| Invite code | `team_invitations.invite_code_hash` | n/a | Check a link. Only the SHA-256 hash is stored; the code cannot be recovered (S4) | n/a | as above |
| Invitation e-mail | `team_invitations.email` | n/a | **Unused**: no code reads or writes it. Do not start using it without updating this page | n/a | as above |
| Timestamps | `*.created_at`, `expires_at`, `revoked_at` | Account holders | Ordering, expiry | Art. 6(1)(f) | with the row |

The database holds **no** date of birth, photo, address, phone number, e-mail address or health
data for players or staff (G4). Mixed-in free text is the only way such data could arrive: the
fields are short (`max_length`), but a club can type anything. The terms forbid it.

### 2.2 Held by the sign-in provider (Supabase Auth, not our tables)

| Data | Source | Purpose | Retention |
|---|---|---|---|
| Google e-mail, name, profile picture URL, Google account id | Google, via Supabase Auth | Sign in and recognise the person | Until the account is deleted from Supabase Auth. **No self-service deletion yet** (#95): on request the operator deletes the Auth user by hand |
| Session and refresh tokens, sign-in time, IP address and browser of sign-ins | Supabase Auth | Keep the person signed in; security | Supabase's own rules; confirm in the Supabase dashboard and DPA |

Our API reads only the token's `sub` (identity) and `user_metadata.full_name` (for the inviter's
name). It never stores the e-mail address or picture.

### 2.3 Never stored

- The generated **DOCX/PDF** contains all the player and staff data above. It is created on demand,
  streamed back and **not persisted**: LibreOffice works in a temporary directory that is deleted
  immediately, and every response carries `Cache-Control: no-store` (G5, S10).
- Request bodies, tokens and invite codes are not logged: the server runs with `--no-access-log`, the
  invite code is a URL path segment, and logs hold ids, not names (S8).

### 2.4 In memory only

| Data | Purpose | Retention |
|---|---|---|
| Client IP address (or the `Fly-Client-IP` header) and user id, as rate-limit counters | Stop abuse of the generate and invitation endpoints | 60 s window, process memory, never written down, lost on restart (#96) |

Fly.io and Cloudflare see IP addresses in their own right as hosting providers (section 5).

### 2.5 In the visitor's browser

All of these are **strictly necessary** for a service the person asked for, so ePrivacy needs no
consent banner, but the notice lists them (G14). There are no cookies, analytics, trackers, session
replay or third-party fonts (the fonts are self-hosted from the build).

| Entry | Store | Content | Written when |
|---|---|---|---|
| Supabase session (key starts with `sb-`) | localStorage | The access and refresh token | After Google sign-in; removed on sign-out |
| `lineup-lang` | localStorage | `hu` or `en` | Only when the visitor clicks the language switch (`Accept-Language` is ignored) |
| `lineup-theme` | localStorage | `light` or `dark` | When the visitor picks a theme |
| `lineup-return-to` | sessionStorage | A same-site path (for example the invite page) | Before the Google round trip; cleared afterwards, closing the tab also clears it |

The lineup form keeps no drafts. Nothing else is stored client-side.

## 3. Minimisation and design choices (G4, G13)

- Players and staff: name, NSSZ number and cap number only. Accounts: a random id; the e-mail stays
  with Supabase Auth.
- Team-scoped access: a person sees only the teams they belong to. Probing another team's id
  returns 404, not 403. Tested in `tests/test_tenant_isolation.py`.
- The opponent directory lists only `id` and `name` of teams that are listed. A new team is listed
  by default (so opponents can be found); an owner can switch it off.
- Invite links are multi-use, expire after 2, 24 or 72 hours, can be revoked and are stored as a hash.
- Sign-up is for **adults (16+)**. Players never sign in (Art. 8 does not apply: adults enter their
  data, G3).

## 4. Retention rules

| Data | Rule | Enforced? |
|---|---|---|
| Invitation links | Deleted 7 days after expiry | Yes, in code (`PURGE_GRACE`) and tested |
| Rate-limit counters | 60 s, memory | Yes, by construction |
| Generated files | Never stored. The lineup creator's PDF preview lives only in browser memory (a `Blob` that is dropped when the panel closes), rendered by pdf.js whose worker is bundled with the app, so no third party sees it | Yes, by construction and tested (`no-store`) |
| Players, saved lineups, teams | Until the club deletes them. Deleting a team needs its players and lineups gone first (409 otherwise) | Manual by the club; a club that stops using the service is cleaned up by the operator on request |
| Saved-lineup snapshots | Keep the player's name/NSSZ **as it was when saved**, so deleting a player does not remove them from old lineups | **Gap**: erasure of one person across snapshots needs a tool (#95) |
| Accounts | Until deleted | **Gap**: no self-service deletion (#95); manual on request |
| Inactive accounts | Proposed: ask the owner and delete after 24 months without sign-in | **Not implemented** (#95) |
| Backups | Section 7 | n/a |

A request is answered within one month (Art. 12(3)). Until #95 lands, access, correction and
erasure are done by the operator by hand, and the procedure is in section 9.

## 5. Sub-processors and transfers

| Service | What it does for us | Data it sees | Region (G10) | Terms |
|---|---|---|---|---|
| **Supabase** | Postgres database and Auth | Everything in 2.1 and 2.2 | AWS `eu-west-1` (Ireland) | [DPA](https://supabase.com/legal/dpa) (accepting the agreement counts as signing the SCCs); [sub-processors](https://supabase.com/legal/customer-resources/subprocessor-list) |
| **Fly.io** | Runs the API container | All API traffic in transit, including the data in 2.1; IP addresses; no database of its own | `ams` (Amsterdam) | [Fly.io legal](https://fly.io/legal); ⚖ confirm the DPA is accepted for this account |
| **Cloudflare** (Pages) | Serves the static web app | Visitors' IP addresses and requests for the web app; no lineup data | Global CDN (EU-pinning is not available on Pages) | [Customer DPA](https://www.cloudflare.com/cloudflare-customer-dpa/); ⚖ accept it for this account |
| **Sentry** | Error reports | **Not active.** No `SENTRY_DSN` is set; before it is (#25), PII scrubbing must exist (#93) and the project must use the EU region | EU, when enabled | [DPA](https://sentry.io/legal/dpa/) |
| **Google** | Sign-in | The person's own Google account | n/a | Independent controller: its [privacy policy](https://policies.google.com/privacy) applies to the sign-in |
| **GitHub** | Source code and CI | **No user data.** The post-deploy smoke test writes only synthetic `smoke-` rows | n/a | Not a processor of user data; the database URL is an Actions secret |

International transfers: Fly.io, Cloudflare, Sentry and Google are US companies. Transfers rely on
the **EU–US Data Privacy Framework** where the provider is certified, with the **standard contractual
clauses** in the DPAs as the fallback. The General Court dismissed the challenge to the DPF
(T-553/23, September 2025), but an appeal is possible: re-check the status at each audit. Data at
rest stays in the EU (Supabase Ireland, Fly Amsterdam).

When a sub-processor is added or replaced, update this table, [[Compliance Records]] and the notice,
and tell the clubs (the terms promise advance notice).

## 6. Lawful basis in short

- **Rosters and lineups (clubs as controllers):** legitimate interest, Art. 6(1)(f): organising
  matches and registering players for them. Consent is deliberately not used (it can be withdrawn
  and is hard to get validly for minors). The written test, with extra weight for children, is in
  [[Compliance Records]]. ⚖ Whether the Sport Act (2004. évi I.) or the MVLSZ registration rules
  make this a legal obligation (Art. 6(1)(c)) is for a lawyer to confirm (H4).
- **Accounts (operator as controller):** providing the service the person signs up for (Art. 6(1)(b))
  and the operator's interest in keeping it secure (Art. 6(1)(f)).

## 7. Backups (S15)

- **Supabase Free plan:** Supabase's backups page states automatic daily backups only for Pro (7
  days) and Team (14 days); for Free it gives no backup or retention promise and recommends that
  you export your data regularly. Treat the dev database as **having no backup**.
- Consequence for erasure: with no backups, deleted data is gone at once; if the project moves to a
  paid plan, deleted data **survives in backups until they expire** (7 or 14 days) and the notice
  must say so. The notice text already says "up to 30 days" to stay safe.
- Restore has never been tested. A backup and restore plan is tracked in #164 (parked).

## 8. What is not built yet

| Gap | Issue | Effect on this page |
|---|---|---|
| Export, erasure across snapshots, account deletion, inactivity purge | #95 | Rights are handled by hand (section 9) |
| Sentry scrubbing before a DSN is set | #93 | Sentry stays off, so it is not a live processor |
| Frontend CSP, privacy page links, footer | #97 | The notice is not yet linked from the app; the sign-in page must link it before inviting anyone |
| Backup and restore | #164 | Section 7 |
| `created_by` columns are not purged on account deletion | #95 | They are random ids; they should be nulled when the account is deleted |

## 9. Handling a data-subject request by hand

1. Answer within one month; confirm the person's identity (for players: through the club).
2. If the person is a **player or staff member**, forward the request to the club (the controller)
   and help it (Art. 28(3)(e)). The club asks the operator to act; do not act on a player's request
   alone.
3. **Access / export:** ask the club to use the app, or run read-only queries for the person's rows
   as the owner role, and send the result to the club.
4. **Correction:** the club edits the player.
5. **Erasure:** delete the player, then the matching `lineup_player_snapshots` rows (by name and NSSZ
   number) and, if needed, the saved lineup. Write what was deleted to the private request log.
6. **Account holder erasure:** remove the person from their teams (the last owner must hand over
   first), then delete the Supabase Auth user in the dashboard.
7. Keep a private note of the request, the date and the answer. Do not put names in the public repo.

## 10. Before inviting anyone: checklist

- [ ] Placeholders in section 1 filled in everywhere (`grep -rn '\[OPERATOR\|\[PRIVACY E-MAIL' documentation`)
- [ ] Notice linked from the sign-in page (#97) and the footer
- [ ] Cloudflare, Fly.io and Supabase DPAs accepted for the account (⚖ one-time legal check)
- [ ] Sentry stays off until #93
- [ ] Clubs have the terms and the Art. 14 template
- [ ] A lawyer has looked at the ⚖ items once ([[Compliance Records]])
