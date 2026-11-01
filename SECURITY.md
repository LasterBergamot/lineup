# Security policy

Lineup is a small project run by one person for a handful of known users. There is one hosted
environment (dev/test); there is no production service and no versioned release line to backport
fixes to. The latest commit on `develop` is the only supported version.

## Reporting a vulnerability

**Please report it privately, not in a public issue or pull request.**

Use GitHub's private vulnerability reporting: open the repository's
[Security tab](https://github.com/LasterBergamot/lineup/security) and choose **Report a
vulnerability** (direct link:
[new advisory](https://github.com/LasterBergamot/lineup/security/advisories/new)). Only the
maintainer can see the report.

Helpful to include: what you found, where (endpoint, page or file), the steps to reproduce it and
what an attacker could do with it. Please do not read, change or delete other people's data to
prove a point: a request that shows you *could* is enough.

## What to expect

This is a hobby project, so these are intentions, not guarantees:

- an acknowledgement within about a week;
- a fix or a decision (with a reason) as soon as the maintainer can, usually within a few weeks;
- credit in the fix, if you want it.

If the report involves personal data (a leak, or access to another team's roster), the maintainer
also follows the [breach runbook](documentation/Breach-Runbook.md), which has its own deadlines.

## Scope

In scope: the API (`backend/`), the web app (`frontend/`), the container image and the GitHub
Actions workflows in this repository.

Out of scope: the third-party services the project runs on (Supabase, Fly.io, Cloudflare, Google
sign-in; report those to the provider), findings that need a stolen password or an already
compromised device, volume-based denial of service, and missing hardening that has no concrete
attack (the API's existing protections are listed in
[Privacy and Security](documentation/Privacy-and-Security.md)).

## Secrets

Never commit secrets. If you find a credential in this repository or its history, report it
privately as above; do not use it.
