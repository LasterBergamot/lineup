# Breach Runbook

What to do when personal data may have been lost, leaked, altered or reached the wrong person
(G11). The clock matters: GDPR Art. 33 gives a controller **72 hours from becoming aware** to tell
NAIH, unless the breach is unlikely to put people at risk. Clubs are the controllers of rosters and
lineups, so for their data we must tell them **without undue delay** (the processor agreement
promises within 48 hours, [[Terms and Processor Agreement]], 2.11). For user accounts we are the
controller ourselves.

Facts about the data are on [[Privacy and Security]]. Not legal advice. `[…]` marks a placeholder.

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
