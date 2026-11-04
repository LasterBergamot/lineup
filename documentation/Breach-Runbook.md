# Breach Runbook

What to do when personal data may have been lost, leaked, altered or reached the wrong person
(G11). The clock matters: GDPR Art. 33 gives a controller **72 hours from becoming aware** to tell
NAIH, unless the breach is unlikely to put people at risk. Clubs are the controllers of rosters and
lineups, so for their data we must tell them **without undue delay** (the processor agreement
promises within 48 hours, [[Terms and Processor Agreement]], 2.11). For user accounts we are the
controller ourselves.

Facts about the data are on [[Privacy and Security]]. Not legal advice. `[…]` marks a placeholder.
The steps below are written for the cloud install; **self-hosted installs** have their own steps
in section 8 (a lost or stolen machine, a compromised tunnel token, a leaked `.env`).

## 1. What counts

A *personal-data breach* is a security incident that destroys, loses, changes, discloses or gives
access to personal data, by accident or on purpose. Examples for Lineup:

- someone sees another team's players (an authorisation bug, a leaked invite link);
- a database URL, API token or signing key leaks (a committed secret, a public log);
- a database or Fly machine is accessed by someone who should not;
- a bug or deploy deletes or corrupts rosters;
- Sentry or logs start recording names or invite codes;
- a lost laptop with the `.env` files, or a phished GitHub or Supabase account.

When unsure, treat it as a breach and decide later: a wrongly raised incident costs an hour, a late
one costs the deadline.

## 2. The first hour

1. **Write down the time you became aware.** The 72 hours start now. Open a private incident note
   (see section 5) and start the timeline.
2. **Contain it.** Pick what applies:
   - Revoke invite links (owners can; or delete the `team_invitations` rows).
   - Rotate the leaked secret: the Supabase `lineup_app` password (`task db:create-app-role`, then update
     the Fly secret `DATABASE_URL` and the Actions secrets `KEEPALIVE_DATABASE_URL`,
     `SMOKE_DATABASE_URL`), the `MIGRATE_DATABASE_URL` owner password, the `FLY_API_TOKEN`
     (`fly tokens revoke`), then see [[Fly Setup]].
   - Sign out all sessions or disable Google sign-in in the Supabase dashboard if tokens are
     compromised.
   - Stop the app: `fly scale count 0 -a lineup-dev-lb` (scale-to-zero machines restart on a request,
     so scale the count, not just stop). Roll back a bad deploy with `fly releases` and `fly deploy`
     of the previous image.
3. **Preserve evidence.** Do not delete logs. Copy the relevant Fly logs, Supabase logs and the
   GitHub Actions run to the private incident folder.
4. **Do not talk about it publicly** yet: not in an issue, a PR or the wiki (the repo is public).

## 3. Assess the risk (within the first day)

Answer in the incident note:

1. What data, whose, how many people, and are any of them **children**?
2. Was it exposed to anyone outside the team, or only to a trusted person who deleted it?
3. Was it readable (not encrypted/hashed)? Invite codes are hashed; names and NSSZ numbers are not.
4. Is it still exposed or can it be misused (for example identity-related)?

Rate the risk:

| Risk to the people | Example | Tell NAIH? | Tell the people? |
|---|---|---|---|
| **None or unlikely** | A secret rotated before anyone could use it; an encrypted backup lost | No, **but log it** | No |
| **Risk** | Player names and NSSZ numbers of a team were visible to another team | **Yes, within 72 h** | Not required unless high risk |
| **High risk** | Data of many children published openly; an account takeover that shows rosters | Yes | **Yes, without undue delay**, in clear language (Art. 34) |

Children's data pushes the rating up. When in doubt, notify.

## 4. Notify

### 4.1 The clubs (we are their processor)

As soon as you know that club data is involved, and within 48 hours at the latest: write to each
affected club's contact with
what happened and when, which data and how many people, what we have done, what the club should do
(it decides whether to notify NAIH and the people), and a contact. Offer help with their notification.
Keep the message factual; do not guess.

### 4.2 NAIH (we are the controller, or the club asks us to file)

File **within 72 hours of becoming aware**, through the online system:
<https://naih.hu/adatvedelmi-incidensbejelento-rendszer>. If a detail is still unknown, file what
you have and add the rest later (Art. 33(4)). If you are late, say why.
The report covers: the nature of the breach and the categories and approximate number of people and
records; the contact; the likely consequences; the measures taken or planned.

### 4.3 The people concerned (high risk only)

Tell them directly (e-mail, or through the club) in clear Hungarian and English: what happened, what
data, likely consequences, what we have done, what they can do, and whom to contact (Art. 34).

### 4.4 Others

If a provider is the cause (Supabase, Fly.io, Cloudflare), use their security contact and ask for
their incident report. If a crime may have been committed, consider reporting to the police.

## 5. The internal breach log

Art. 33(5) requires a record of **every** breach, including those not reported. Keep it **privately**,
not in this repo (it is public) and not in the wiki. A spreadsheet or a private note is enough. One row
per incident:

| Field | Content |
|---|---|
| ID and dates | Incident ID; time of becoming aware; time contained; time closed |
| What happened | Facts, cause, how found |
| Data and people | Categories, approximate numbers, children involved (yes/no) |
| Risk rating | None / risk / high, with the reasoning |
| Notified | Clubs (when, who), NAIH (when, reference number), people (when, how), or "not required" with the reason |
| Actions | Containment, fix, secrets rotated |
| Follow-up | Issue number for the lasting fix, changes to docs or tests |

A short, **non-personal** lessons-learned summary may go into a public issue after the incident is
closed.

## 6. After it

- Fix the cause and add a test that fails without the fix.
- Rotate anything that was exposed, even if you think it was not used.
- Update [[Privacy and Security]], [[Compliance Records]] or this runbook if the incident showed a gap.
- Review the incident in the next audit (`compliance-audit`).

## 7. Contacts (fill in)

| Who | Contact |
|---|---|
| Operator / incident lead | [OPERATOR NAME], [PRIVACY E-MAIL] |
| NAIH | <https://naih.hu/adatvedelmi-incidensbejelento-rendszer>, ugyfelszolgalat@naih.hu |
| Supabase | Dashboard support (ask for their incident report) |
| Fly.io | Dashboard support, community.fly.io |
| Clubs | Kept privately, with the Art. 30 processor record |
| Cloudflare (self-hosted installs) | Dashboard support for the account that owns the tunnel |
| The machine's owner (self-hosted installs) | `[MACHINE OWNER CONTACT]`, kept privately |

## 8. Self-hosted installs

For an install on one machine behind a Cloudflare Tunnel ([[Privacy and Security]], section 11).
Sections 1 to 6 apply unchanged (the 72 hours, the risk rating, who to tell). What differs is
**what can go wrong**, **what to contain** and **what to rotate**. Self-hosting does not remove any
duty to log or report a breach. Never write the machine's location, owner or domain into an issue,
PR or the wiki; keep the incident note private (section 5).

Three facts shape every case below:

- **Backups are on the same machine and are not encrypted.** There is **no other copy** of the
  data. Losing the machine is also a loss of availability, which is a breach (Art. 4(12)) even if
  nobody read anything.
- **All secrets are in one file, `selfhost/.env`** on the machine (mode 600).
- **Cloudflare sees the traffic decrypted** and the tunnel token lets a program act as the machine's
  connector.

### 8.1 What to rotate, and how

Rotating means: put a new value in `.env`, restart the services that read it, and check the app.
The exact commands (a restart, an update) are in the operator guide for the install. Which value
sits where:

| Secret (name in `.env`) | When | How to get a new value | Effect of rotating |
|---|---|---|---|
| `TUNNEL_TOKEN` | Token seen by anyone else; machine lost | Cloudflare dashboard, Zero Trust, Networks, Tunnels, the tunnel: refresh its token (or delete the tunnel, create a new one, give it the same public hostname and use the new token) | The old token stops working; the site is down until the new token is in `.env` and the tunnel service is restarted |
| `GOOGLE_SECRET` (and `GOOGLE_CLIENT_ID`) | Leaked `.env`; machine lost | Google Cloud console, the sign-in project, Clients: add a new client secret, then disable the old one | The old secret stops working; sign-in is down until `.env` has the new one and the Auth service is restarted |
| `AUTH_JWT_KEYS` (and `AUTH_JWT_SECRET`) | Leaked `.env`; machine lost; traffic exposed | Generate a new signing key with `python -m lineup.auth.signing_key` (from `backend/` in a checkout, on any computer, never pasted into a chat); the value is a JSON array on **one line in single quotes** | Every access token signed with the old key is rejected, so **everyone is signed out** and signs in again. This is also the quickest way to end all sessions |
| `POSTGRES_PASSWORD`, `AUTH_DB_PASSWORD`, `LINEUP_APP_PASSWORD` | Leaked `.env`; machine lost | Choose new URL-safe values (letters and digits only; two of them sit inside connection URLs) and change the matching database roles to the same values, then restart | The services reconnect with the new passwords. Change a database role's password and `.env` together, or the service cannot connect |

After any rotation: check that sign-in works, that a PDF generates, and write down in the incident
note what you rotated and when. A rotated secret that was **not** exposed costs nothing, so when
unsure, rotate.

If invite links might have been exposed too, revoke them (an owner can, section 2).

### 8.2 The machine is lost or stolen

1. **Write down when you became aware** (the 72 hours start). Ask the machine's owner for the facts:
   when it was last seen, whether it was switched off, whether full-disk encryption was on.
2. **Cut the access first.** Delete the tunnel in the Cloudflare dashboard, or refresh its token, so
   a thief who powers the machine on cannot be reached from the internet. Disable the Google client
   secret in the Google Cloud console.
3. **Assume the secrets in `.env` are known** unless the disk is encrypted and the machine was off:
   rotate everything in 8.1 for the *replacement* install. Sessions on the old machine cannot be
   revoked from outside, but the new signing key and the new Google secret make them useless.
4. **Rate the risk (section 3).** With full-disk encryption and a machine that was off, the data is
   likely unreadable, so the risk may be **unlikely** (log it, do not file, ⚖ record the reasoning).
   Without encryption, treat names and NSSZ numbers of players, some of them children, as exposed:
   that is a **risk** or **high risk** case, and the unencrypted backups are on the same disk.
5. **Availability.** There is no off-machine backup. Tell the clubs at once (4.1): they may need to
   re-enter their rosters. Set up the replacement install with new secrets; a copy of the data exists
   only if the operator took a backup elsewhere.
6. If the owner and the operator are different people, the processor agreement requires the owner to
   report within the agreed time; tell the clubs within 48 hours of the operator becoming aware.

### 8.3 The tunnel token is compromised

Someone with the token can run their own connector for your tunnel, and Cloudflare may send some of
the site's requests to it. They would see **requests and responses in the clear: tokens, invite
codes in URLs, lineup data and PDFs**.

1. Note the time. **Refresh the token** in the Cloudflare dashboard (or delete and recreate the
   tunnel) straight away; this cuts the other connector off.
2. In the tunnel's page, look at the list of connectors and write down any you do not recognise
   (address and time; this is evidence).
3. Update `TUNNEL_TOKEN` in `.env` and restart the tunnel service. Check the site works.
4. **Sign everyone out** by rotating `AUTH_JWT_KEYS` (8.1): bearer tokens may have been seen. Revoke
   invite links.
5. Rate the risk (section 3) for the period between the leak and the refresh: what the connector
   could have seen. Children's data was inside the traffic, so lean towards notifying.
6. Check how the token leaked (a pasted command, a screenshot, a chat, a shared screen) and close
   that hole.

### 8.4 The `.env` file leaked

It holds the database superuser password, the signing key and the Google and tunnel secrets.

1. Note the time and **how far the file went** (a public repo or paste, a chat, a backup, an
   e-mail attachment, someone's screen share). A copy in a private chat only seen by the operator
   is a smaller incident than one on a public page.
2. If the file was public, even briefly, assume it was copied.
3. Rotate **everything** in 8.1, in this order: the tunnel token and the Google secret (so nobody
   can impersonate the site or sign in), then the signing key (ends sessions), then the database
   passwords.
4. The databases are only reachable from inside the machine's private network (no port is open), so
   a leaked database password alone does not give outside access. Still rotate it, and check that
   nobody else has a shell on the machine.
5. The backups do **not** contain `.env`, but they contain the data. If someone had access to the
   machine, treat it as 8.2 step 4.
6. If it was committed to a repo, removing it from history is not enough: the secrets are rotated
   in step 3 regardless. Tell GitHub support if a public repo held it.

### 8.5 Evidence on the machine

Container logs are small by design (Docker keeps 3 files of 10 MB per service, and there are no
access logs), so **copy them before restarting the services**, to the private incident folder.
They hold ids and error messages, not names or tokens. Cloudflare's dashboard shows the tunnel's
connectors and its own logs for the account.
