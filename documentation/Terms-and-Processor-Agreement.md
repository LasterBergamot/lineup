# Terms and Processor Agreement

Two texts that clubs and users accept before they use Lineup (G3, G9):

1. **Terms of use** for everyone who signs in.
2. **Processor agreement** (GDPR Art. 28(3)) between each club (controller) and the operator
   (processor). Accepting the terms on behalf of a club accepts this agreement.

The facts behind them (data, retention, sub-processors) are on [[Privacy and Security]]; the
information given to players is in [[Privacy Notice]]. `[…]` marks a placeholder the operator fills in.
Not legal advice: both texts need a lawyer's read once before real clubs sign up (⚖). The app will
show them at first sign-in (#97); until then this file is the source.

---

## 1. Terms of use

1. **What Lineup is.** A web tool that keeps a team's roster and prepares the match lineup sheet as a
   PDF or DOCX. It is run as a small, free, best-effort service by [OPERATOR NAME] (the "operator"),
   currently as a **dev preview**: it may change, break or be reset, and data may be deleted without
   notice during the preview. Keep your own copy of anything that matters.
2. **Who may sign in.** You must be **16 or older** and sign in with a Google account. If you act for a
   club you confirm you are allowed to do so. Players do not sign in.
3. **Your responsibilities.** You enter only the data the sheet needs: names, federation (NSSZ) numbers
   and cap numbers of players, and the names of staff. **Do not enter** dates of birth, photos, contact
   details, health information, or anything not needed for the sheet. The "doctor" field is for a name
   only. Enter data about people only if your club is entitled to, and give them the information in the
   club template ([[Privacy Notice]], section 3). Do not share invite links publicly; anyone with a
   link can join the team until it expires or is revoked. Do not try to reach other teams' data, probe
   or overload the service, or use it for anything unlawful.
4. **Your data.** The club keeps all rights to its data. The operator uses it only to run the service
   (section 2 below) and not for advertising or anything else.
5. **Availability and liability.** The service is provided "as is", without a guarantee of availability
   or accuracy. **Check every generated sheet before you hand it in.** To the extent the law allows,
   the operator is not liable for indirect loss or for a sheet that is wrong or late. Nothing here
   limits liability that cannot be limited by law (for example for intent or for harm to life, body or
   health). ⚖
6. **Ending.** You can stop at any time and ask to delete your account and your club's data. The
   operator can suspend access for misuse or end the preview with reasonable notice (at least 14 days
   where possible, so clubs can export).
7. **Changes.** The operator may change these terms; for material changes, signed-in users are told
   before they apply. Continued use after the notice means acceptance.
8. **Law and disputes.** Hungarian law applies. Consumers keep their mandatory rights. Courts of
   Hungary have jurisdiction, subject to mandatory rules. ⚖
9. **Contact.** [PRIVACY E-MAIL].

---

## 2. Processor agreement for clubs (Art. 28(3))

**Parties.** The club that uses Lineup (the *controller*) and [OPERATOR NAME], [OPERATOR ADDRESS] (the
*processor*). It applies for as long as the club uses Lineup.

**2.1 Subject matter and duration.** The processor stores and processes the club's roster and lineup
data in order to provide Lineup, for as long as the club uses it, until the data is deleted as in 2.9.

**2.2 Nature and purpose.** Storing, displaying and editing players, staff and lineups, and rendering
lineup sheets as DOCX/PDF on request. No other purpose.

**2.3 Data and people.** Types of data: names, NSSZ numbers and cap numbers of players; names of staff
(coach, doctor, assistant coach, team leader, ball thrower); team and match details; the user ids and
roles of the club's account holders. Data subjects: the club's players (some are children), staff, and
account holders. The full inventory is on [[Privacy and Security]].

**2.4 Instructions.** The processor processes the data **only on the controller's documented
instructions**: these terms and what the club's users do in the app. If the processor believes an
instruction breaks data-protection law, it tells the controller. If the law requires the processor to
act otherwise, it tells the controller first unless the law forbids it. (Art. 28(3)(a))

**2.5 Confidentiality.** Everyone who can access the data at the processor is bound to confidentiality.
(Art. 28(3)(b))

**2.6 Security.** The processor applies the measures of Art. 32. Those in place today are:

- every request needs a signed-in user; the identity token is checked against the sign-in provider's
  public keys, and people see only the teams they belong to;
- encryption in transit (TLS) and database access through a least-privilege database role with
  row-level security;
- invite links with at least 128 bits of randomness, stored only as a hash, expiring and revocable;
- security headers, request size and rate limits, and no personal data in logs;
- generated files are never stored;
- dependency and secret scanning in the code repository.

Backups follow the hosting plan (see [[Privacy and Security]], section 7). (Art. 28(3)(c))

**2.7 Sub-processors.** The controller gives **general authorisation** for the sub-processors on
[[Privacy and Security]] (section 5): Supabase, Fly.io and Cloudflare, and Sentry once enabled. The
processor binds each to the same obligations by contract, stays responsible for them, keeps data at
rest in the EU, relies on the EU–US Data Privacy Framework or the standard contractual clauses for
transfers, and **tells the controller at least 14 days before** adding or replacing one. The
controller may object on reasonable grounds within that time; if the parties cannot agree, the
controller may stop using Lineup and have its data deleted. (Art. 28(2), (4))

**2.8 Assisting the controller.** The processor helps the controller to answer data-subject requests
(access, correction, erasure, restriction, portability, objection) and to meet its duties on
security, breach notification, impact assessments and consultation (Arts. 32–36), taking account of
the nature of processing. Today the processor does the technical part of a request by hand within
**10 working days** of the controller asking; the app will get export and deletion features (#95).
(Art. 28(3)(e), (f))

**2.9 Return and deletion.** When the controller stops using Lineup, or asks, the processor deletes
the club's data (teams, players, saved lineups, memberships) or returns it in a common format, within
**30 days**, and confirms. Copies in provider backups expire on the backup schedule (up to 30 days).
Data the law requires the processor to keep stays protected and is not used. (Art. 28(3)(g))

**2.10 Audits.** The processor gives the controller the information needed to show compliance
(this agreement, the records on [[Compliance Records]], the sub-processor list) and allows reasonable
audits, with notice, at the controller's cost, in a way that does not disturb other clubs.
(Art. 28(3)(h))

**2.11 Personal-data breaches.** The processor tells the controller **without undue delay and in any
case within 48 hours** of becoming aware of a breach affecting its data, with what it knows: the
nature, the data and people concerned, likely consequences, measures taken, and a contact. The
controller decides about telling NAIH (72 hours from its own awareness) and the people concerned. See
[[Breach Runbook]]. (Art. 33(2))

**2.12 Liability and law.** Each party is liable as GDPR Art. 82 provides. Hungarian law applies. ⚖

**2.13 Roles of the club.** The club confirms that it has a lawful basis for putting the data into
Lineup, has given players, staff and parents the information in the club template ([[Privacy Notice]],
section 3), and only enters the data categories listed in 2.3.
