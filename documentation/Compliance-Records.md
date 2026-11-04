# Compliance Records

The written records GDPR asks us to keep (G2, G8, G12), one section each:

1. [Art. 30 record: the operator as controller (user accounts)](#1-art-30-record-operator-as-controller)
2. [Art. 30 record: the operator as processor (clubs' data)](#2-art-30-record-operator-as-processor)
3. [Legitimate-interest assessment (Art. 6(1)(f))](#3-legitimate-interest-assessment)
4. [DPIA screening note (Art. 35)](#4-dpia-screening-note)
5. [Self-hosted installs: Art. 30 variant and updated DPIA screening](#5-self-hosted-installs)

All facts come from [[Privacy and Security]]; keep them in step. The Art. 30(5) exemption for
organisations under 250 people **does not apply**, because the processing is not occasional and
includes children's data. Not legal advice: ⚖ items want a lawyer's look once.

`[…]` marks a placeholder the operator fills in. Review these records at least once a year and
whenever a data category, a sub-processor or a purpose changes. *Last reviewed: [DATE].*

---

## 1. Art. 30 record: operator as controller

(Art. 30(1): user accounts.)

| Item | Entry |
|---|---|
| Controller | [OPERATOR NAME], [OPERATOR ADDRESS], [PRIVACY E-MAIL]. No joint controller, no representative, no DPO |
| Purposes | Letting people sign in; deciding which teams they may see and edit; auditing who created what; invitation links; preventing abuse |
| Data subjects | Account holders (club staff and volunteers, aged 16+) |
| Categories of data | Google e-mail, name, picture and account id (held by Supabase Auth); random user id, team role, join date, inviter's display name, creator ids; IP address and user id as 60-second in-memory counters |
| Recipients | Supabase (database and sign-in), Fly.io (API hosting), Cloudflare (web hosting); Google is a separate controller |
| Transfers outside the EU/EEA | Possible by Fly.io, Cloudflare and Google (US): EU–US Data Privacy Framework, standard contractual clauses as fallback. Data at rest: Supabase `eu-west-1`, Fly `ams` |
| Retention | Account until deleted (manual for now, #95); invite links 7 days after expiry; rate-limit counters 60 s; see the inventory |
| Security measures (Art. 32) | See section 2 below and the list in [[Terms and Processor Agreement]], 2.6 |

## 2. Art. 30 record: operator as processor

(Art. 30(2): rosters and lineups, on behalf of clubs.)

| Item | Entry |
|---|---|
| Processor | [OPERATOR NAME], [OPERATOR ADDRESS], [PRIVACY E-MAIL]. No DPO |
| Controllers | Each club with a team in Lineup. The list of clubs is kept privately by the operator (it is not published in this repo) |
| Categories of processing | Storing, displaying and editing player, staff and lineup records; rendering DOCX/PDF on request |
| Categories of data and subjects | Players (some children): name, NSSZ number, cap number. Staff: names. Team and match details |
| Sub-processors | Supabase, Fly.io, Cloudflare (Sentry once enabled) |
| Transfers outside the EU/EEA | As in section 1 |
| Instructions | The [[Terms and Processor Agreement]] and what the club's users do in the app |
| Security measures (Art. 32) | TLS in transit; token-checked access, team-scoped queries (404 for other teams' ids); least-privilege database role with row-level security; hashed, expiring, revocable invite codes; security headers, body-size and rate limits; no personal data in logs, no access log; generated files never stored and sent `no-store`; secrets only in platform stores; CI scanning of dependencies and secrets; synthetic-only smoke tests |

---

## 3. Legitimate-interest assessment

**Processing assessed:** keeping a club's player and staff names and NSSZ numbers in Lineup, and
printing them on the match lineup sheet. The interest is the **club's** (the controller); the
operator supports it as processor. Consent is not used: it could be withdrawn mid-season, is hard to
get validly for children and would not fit a registration duty. (EDPB Guidelines 1/2024)

**Step 1: purpose test. Is there a legitimate interest?**
Yes. A club must give the match officials a lineup sheet with the registered players for every match.
Preparing it quickly and correctly is a real, lawful and specific interest, and the club and the
federation both expect the sheet.

**Step 2: necessity test. Is the processing needed for it?**
Yes, for the fields used. The sheet needs a name, the registration number and the cap number, nothing
more, and that is all Lineup stores: no date of birth, photo, contact details or health data (G4). A
less intrusive way (typing the sheet by hand) exists, but would still use the same three fields, so
the data is not reduced by it. Keeping a roster between matches means the data is entered once
instead of re-typed for each match.

**Step 3: balancing test.**

| Factor | Assessment |
|---|---|
| Nature of the data | Ordinary personal data. Name and a federation number are already shown on printed sheets handed to officials. **No special categories** (the doctor field is a name) |
| Data subjects | Players, **some under 18**, and staff. Children get extra weight: they cannot easily assess the risk, and the data comes from the club, not from them |
| Reasonable expectations | A player expects the club to give their name and registration number to the match officials; that is the point of a lineup. They would not expect it to be shown to strangers, which it is not (team-scoped access; only the team name is ever public) |
| Impact | Low. Likely harm is a wrong sheet or an unauthorised person seeing a name and number. No profiling, no automated decisions, no publication, no sale, no tracking |
| Safeguards | Team-scoped access, token-checked sign-in, hashed expiring invites, data in the EU, no files stored, no logging of personal data, the club-facing Art. 14 notice, erasure and objection on request, minimal fields |
| Right to object | The notice tells people they can object (Art. 21). The club (and the operator for it) then stops using that person's data unless it shows overriding grounds. For a lineup, a refused player is simply left off the sheet |

**Outcome.** The balance favours processing: the interest is genuine, the data is minimal and low
risk, the safeguards are proportionate, and people can object. It needs to be **re-done** if the app
adds any new field about people, publishes data, or uses it for anything beyond the sheet.

**Open points ⚖.**
1. Whether the Sport Act (2004. évi I.) or the MVLSZ registration rules make the club's use a legal
   obligation (Art. 6(1)(c)) so that the clubs can rely on that instead (H4). If so, update the
   notice templates.
2. Whether a club's use for amateur or youth teams needs anything extra for under-14s (parents act,
   Ptk. 2:10–2:12; H3). The notice already lets the parent make requests.

---

## 4. DPIA screening note

**Question (Art. 35):** is a data protection impact assessment required? A DPIA is required where
processing is likely to result in a **high risk**. The EDPB lists nine criteria (evaluation or
scoring, automated decisions, systematic monitoring, sensitive data, large scale, matching datasets,
vulnerable subjects, innovative technology, blocking a right or service); two or more usually mean
a DPIA. NAIH publishes its own list of processing that needs one (⚖ check the current list).

| EDPB criterion | Applies? | Reason |
|---|---|---|
| Evaluation or scoring | No | Nothing is scored or profiled |
| Automated decision with legal effect | No | None |
| Systematic monitoring | No | No tracking, no analytics; only 60-second counters |
| Sensitive or highly personal data | No | No special categories; names and a registration number |
| Large scale | No | A handful of clubs, hundreds of people at most |
| Matching or combining datasets | No | One dataset per club |
| Vulnerable data subjects | **Yes** | Some players are children |
| Innovative technology | No | A standard web app |
| Blocking a right or service | No | Nothing depends on the lineup tool by law |

**Conclusion.** Only one criterion (children) applies, the scale is small, there is no profiling and
no sensitive data, so a **full DPIA is not required**. The children criterion is the reason we
treat the data with more care anyway (weight in the LIA, minimal fields, no public data beyond team
names, team-scoped access).

**Triggers to re-screen:** a new data field about people (especially a date of birth, photo, health or
contact data), publishing rosters, analytics or error reporting that can see personal data (Sentry,
#93), a large increase in the number of clubs, or any use beyond the lineup sheet.

*Screened by: [OPERATOR NAME] on [DATE].*

---

## 5. Self-hosted installs

For an install on one machine behind a Cloudflare Tunnel ([[Privacy and Security]], section 11).
Self-hosting does not remove GDPR: both Art. 30 records and the screening still apply, and the
legitimate-interest assessment (section 3) is unchanged because the purpose, the fields and the
people are the same. Keep **one set of these records per install**, privately, with the install's
own entries below. Facts that identify the machine (its owner, place, address) stay in the
operator's private record and never go in this repo. *Last reviewed: [DATE].*

### 5.1 Art. 30 record, operator as controller (variant)

The same as section 1, with these entries changed:

| Item | Entry |
|---|---|
| Categories of data | As section 1, but the Google e-mail, name, picture and account id, sessions and the IP address and browser of sign-ins are held in the install's own `auth` database on the machine, not by Supabase |
| Recipients | Cloudflare (tunnel and DNS; sees all traffic decrypted), the machine's owner if different from the operator (physical custody); Google is a separate controller. **Not used:** Supabase, Fly.io, Cloudflare Pages |
| Transfers outside the EU/EEA | Possible by Cloudflare (global network, no EU pinning on the free plan) and Google: EU–US Data Privacy Framework, standard contractual clauses as fallback. **Data at rest** stays on the machine, located in the EU/EEA (`[MACHINE LOCATION]`, recorded privately) |
| Retention | As section 1; backups on the machine hold deleted data for up to 30 days |
| Security measures (Art. 32) | See 5.2 and [[Privacy and Security]], section 11.7 |

### 5.2 Art. 30 record, operator as processor (variant)

The same as section 2, with these entries changed:

| Item | Entry |
|---|---|
| Sub-processors | Cloudflare (tunnel and DNS) and, if different from the operator, the machine's owner (`[MACHINE OWNER NAME]`, agreement dated `[AGREEMENT DATE]`). **Not used:** Supabase, Fly.io, Cloudflare Pages |
| Transfers outside the EU/EEA | As 5.1 |
| Security measures (Art. 32) | The measures in section 2 that are application-level (token-checked access, team-scoped queries, hashed invite codes, security headers, rate limits, no personal data in logs, generated files never stored), **plus**: no published port, the only way in is the outbound tunnel; database and API on a network with no internet route; least-privilege database roles; containers with all capabilities dropped and images pinned by digest; secrets in a mode-600 file; no access logs and rotated container logs (3 × 10 MB); a nightly backup, 30 days, same machine, not encrypted, token tables excluded; full-disk encryption on the machine if the hardware supports it; updates are run by hand by a named person |

### 5.3 DPIA screening, updated

Same criteria and conclusion as section 4, re-checked for this variant:

| EDPB criterion | Applies? | Reason for the self-hosted variant |
|---|---|---|
| Systematic monitoring | No | Nothing is monitored by the operator. Cloudflare sees traffic as a network provider; the operator keeps no access logs |
| Large scale | No | Even smaller than the cloud install: a few known people. **Re-screen if that stops being true** |
| Vulnerable data subjects | **Yes** | Some players are children (unchanged) |
| Others | No | As section 4 |

**Conclusion.** Still only one criterion applies, so a **full DPIA is not required**. The variant
changes the *risks*, not the criteria, and these residual risks are accepted knowingly:

| Residual risk | Why accepted | Mitigation |
|---|---|---|
| The machine can be lost, stolen or read by whoever holds it, and the backups are on it, unencrypted | Few people, ordinary data, no special categories | Full-disk encryption if supported; a locked room; processor agreement with the machine's owner; backup folder readable only by the install's user |
| Cloudflare sees the traffic decrypted | Needed for a tunnel with no open port | DPA accepted; named in the notice; no access logs at the origin |
| Nobody updates the install | No automatic updates by design | A named person and a reminder; the pre-invite checklist ([[Privacy and Security]], 11.8) |

**Extra triggers to re-screen:** more than a few known people use the install, backups move to
another place or provider, the machine is moved or its owner changes, or a feature beyond the
lineup sheet is added.

*Screened by: [OPERATOR NAME] on [DATE].*
