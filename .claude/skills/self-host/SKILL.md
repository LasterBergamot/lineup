---
name: self-host
description: Set up, update, back up, restore or check the optional self-hosted Lineup install (a NAS or small server behind a Cloudflare Tunnel) — walk through the manual preparation, then drive `selfhost/lineup.sh` and `task deploy`. Use when asked to self-host, install Lineup on a NAS or server, prepare the domain/tunnel/Google sign-in for it, or update, back up, restore or check that install. Not for the cloud deployment on Fly.io and Cloudflare Pages.
model: haiku
effort: high
---

Helps someone with no IT background run Lineup on one always-on machine. Usage:
`/self-host [prepare|doctor|install|status|update|backup|restore]`. With no argument, run step 1
and ask which one the person wants.

The steps themselves live in the docs, so people and agents follow the same text. **Change the
steps there, not here:** `self-host-plan.md` part M while that file exists,
`documentation/Self-Hosting-Guide.md` and `documentation/Sajat-Gepes-Telepites.md` (Hungarian) for operators, `documentation/Self-Hosting-Reference.md` for the technical detail.

## Rules

- **Never read or print secrets:** `selfhost/.env`, `.env` on the machine, `~/.config/lineup/selfhost.env`,
  tokens, passwords. Ask the person to put a value into the private file themselves; never ask them to
  paste it into this chat. Tell them to check a value's presence with `grep -c '^NAME=' <file>`, which
  shows a count and not the value.
- **Keep the deployment private.** The repo, wiki, issues and PRs are public. Never write who owns or
  hosts the machine, where it is, its model, its real domain, hostname or IP in any of them.
- **Ask before anything that changes the machine or the outside world** (`install`, `update`, `restore`,
  starting a workflow, creating or changing an issue). `doctor` and `status` are read-only.
- **Explain in plain words** what is about to happen, what you expect to see, and what a failure means.
  Do not assume the person knows what a terminal, Docker or a tunnel is.
- Never weaken a check, retry a destructive command or improvise a workaround when a step fails. Stop,
  say what failed and what you suggest.
- Self-hosting does **not** remove GDPR. Before any real data goes on the machine, the checklist in
  `documentation/Privacy-and-Security.md` (self-hosted section) must be complete. Until then, made-up data only.

## 1. Find out what exists

```bash
test -f selfhost/lineup.sh && echo "tool: yes" || echo "tool: no"
test -f self-host-plan.md && echo "plan: yes" || echo "plan: no"
gh release view --json tagName,assets --jq '.tagName, (.assets | map(.name) | join(", "))'
test -f ~/.config/lineup/selfhost.env && stat -c '%a' ~/.config/lineup/selfhost.env
```

- **No `selfhost/lineup.sh`:** the tool is not built yet (see the epic named at the top of
  `self-host-plan.md`). Only `prepare` is available. Say so plainly and do not invent commands.
- **Tool exists, but no release has a `selfhost-v*.tar.gz` asset:** nothing can be installed yet. A release
  needs the owner's go-ahead (`.claude/context/workflow.md`).
- The private file must have mode `600`. If not, ask the person to run `chmod 600` on it.

## 2. `prepare`: the manual steps

Follow part M of `self-host-plan.md` in order, or the "Before you start" section of the guide once that
file is gone: check the machine, decide who operates it, buy the domain, create the tunnel, create the
Google sign-in, accept the backup limits, decide the compliance facts.

For each step: say why it is needed, give the clicks, wait for the person, then check what you can without
seeing a secret. Dashboards change, so if a button is missing, ask what they see and find the closest match.

Record only the architecture and RAM on the manual-preparation issue, nothing else about the machine, and
close the issue when part M's "done when" is met.

## 3. `doctor`

On the machine, run `./lineup.sh doctor`, over SSH if the private file has the values:

```bash
# Reads only these two values, without sourcing the file or printing them.
target=$(sed -n 's/^LINEUP_SELFHOST_SSH=//p' ~/.config/lineup/selfhost.env)
dir=$(sed -n 's/^LINEUP_SELFHOST_DIR=//p' ~/.config/lineup/selfhost.env)
ssh "$target" -- "cd '$dir' && ./lineup.sh doctor"
```

Before the tool is on the machine, use the read-only commands in part M1. Explain every warning or problem.
Stop on any problem: an install on an unsuitable machine fails later and less clearly.

## 4. `install`

1. Confirm `prepare` is finished, and read the backup limits to the person. They must accept them: same
   machine only, not encrypted, **losing the machine loses the data**.
2. Download the newest `selfhost-v*.tar.gz` and its `.sha256` from the GitHub release, and verify before use.
3. With SSH: copy the bundle and the private file to the machine with `scp`, extract the bundle, run
   `./lineup.sh install --from-file <file> --accept-backup-limits`, then **delete the copied file**. Without
   SSH: walk the person through `./lineup.sh install` on the machine, where the script asks for the values
   itself with hidden input.
4. Tell them to save the generated `.env` somewhere safe and private, off the machine.
5. Run step 5, then the external checks in the guide's "Check it works".

## 5. `status`

`./lineup.sh status`. Report in plain words: is the app healthy, how old is the last backup (over 36 hours is
a problem), how much disk is left, and whether a new version exists. Never paste secrets from a log.

## 6. `update`

From a developer machine: `task deploy -- --local`. On the machine: `./lineup.sh update`. Say it takes a backup
first, that the app is briefly unavailable, and pick a quiet time. If it fails, **follow what the script says**.
It either undid the update itself, or it explains the restore; do not improvise. Cloud deploys are separate:
`task deploy -- --cloud`, or simply a push to `develop`.

## 7. `backup` and `restore`

- `./lineup.sh backup` takes one now. Backups also run nightly and are kept for 30 days.
- `./lineup.sh restore`: **destructive.** Say plainly that everything after the chosen date is lost and everyone
  must sign in again, and get an explicit yes for this restore. The script takes a safety backup and asks for a
  typed word: the person types it, or you pass `--yes-restore` only after that explicit yes.

## 8. Report

Say what was done, what you checked and how, what you could not check, and what the person should do next.
Never include the real domain, host or any secret in a report that goes to GitHub.
