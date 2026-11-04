# Self-Hosting Guide

How to run your own copy of Lineup on one always-on machine (a NAS or a small server), step by step,
written for people who have never used a terminal. The Hungarian version, with the same steps in the
same order, is [[Saját gépes telepítés]]. Developers who want the architecture and the details should read
[[Self-Hosting Reference]].

This guide uses `lineup.example.com` everywhere. Replace it with your own domain.

Contents:

1. [What this is](#1-what-this-is)
2. [Before you start](#2-before-you-start)
3. [Install](#3-install)
4. [Check it works](#4-check-it-works)
5. [Add or remove a person](#5-add-or-remove-a-person)
6. [Everyday](#6-everyday)
7. [Update](#7-update)
8. [Backups](#8-backups)
9. [Restore](#9-restore)
10. [When something is wrong](#10-when-something-is-wrong)

---

## 1. What this is

Lineup normally runs in the cloud. This guide is about the **second, optional way**: your own copy,
running on a machine that you (or someone you trust) own and keep switched on. It has its own data and its
own list of people who may sign in. It does not share anything with the cloud copy.

**What you end up with.** A web address such as `https://lineup.example.com` that works from any phone or
computer. People sign in with their Google account, and only the accounts you put on a list can get in.
The machine does not open any door to the internet: the connection goes through a service called a tunnel
(explained below), which is what keeps the machine hidden and safe.

**How long it takes.** Set aside about an hour for the first setup. Most of it is creating accounts
and copying values from one web page to another. After that, the daily work is nothing, and an update takes a
few minutes.

**What it costs.** The domain, about EUR 10 a year. The Cloudflare and Google parts are free, and
Lineup itself is free. The machine and its electricity are yours.

**Who should do the first setup.** Someone careful, not necessarily technical: you will create accounts, copy
values exactly and type a few commands. If you can follow a recipe, you can do this. Doing it with a second
person reading the steps aloud helps.

**Words you will meet.** Each one is explained once here:

- **Terminal**: a window where you type a command and press Enter instead of clicking. On a NAS it
  is often called "Terminal" or "SSH" in the settings. Everything you type there is shown in a grey box in
  this guide: copy it exactly.
- **Docker**: a program that runs other programs in sealed boxes (called containers), so they do not
  interfere with the machine. Lineup is delivered as a set of such boxes. You only need to know that Docker has to
  be installed and running.
- **Domain**: the name of a website, such as `lineup.example.com`. You buy it once a year.
- **Tunnel**: a private pipe from the machine to Cloudflare (a company that runs part of the internet).
  Visitors go to Cloudflare, Cloudflare passes the request through the pipe to your machine. Because the
  machine calls out to Cloudflare, nobody has to be able to call in.
- **Backup**: a copy of the data made so that a mistake or a failed update can be undone. How Lineup's backups
  work, and what they do **not** protect against, is in [section 8](#8-backups). Please read that section
  before you put real data in.

**One more thing before real people use it.** Running Lineup yourself does **not** take it out of the data
protection law (GDPR). Whoever runs it is responsible for the data of the people in it. Until the privacy checklist on
[[Privacy and Security]] (the section on self-hosted installs) is done, use only made-up names and data.

**A note on wording.** Websites such as Cloudflare and Google change their menus often. This guide has no
screenshots for that reason. It names the buttons as they are at the time of writing; if you cannot find one,
**look for the closest wording**.

**Keep your values in one private file.** In the steps below you will collect a few values (an address, a
token, a client id). Keep them in one note on **your own computer**, never in an e-mail or a chat. If you
use a plain text file, make it private: in a terminal on your computer, run
`mkdir -p ~/.config/lineup && touch ~/.config/lineup/selfhost.env && chmod 600 ~/.config/lineup/selfhost.env`.
A password manager works just as well.

---

## 2. Before you start

Six things have to be ready before you install. They do not depend on each other much, so you can do them in
any order, but do all of them.

### 2.1 Check the machine

The machine needs to be switched on all the time, have Docker installed, at least 2 GB of memory (4 GB is
comfortable) and at least 10 GB of free disk.

**Do.** Open a terminal **on the machine**. On a NAS, look in the settings for "Terminal" or "SSH" (turn it on if
needed) and connect from your computer, or use the terminal app the vendor provides. Then copy this line,
paste it and press Enter:

```bash
uname -m; grep MemTotal /proc/meminfo; df -h .; docker --version; docker compose version
```

**You should see.** About five groups of lines:

- `x86_64` or `aarch64` (the kind of processor; either works),
- `MemTotal:` followed by a number of at least 2000000 (that is kilobytes: 2 GB),
- a table where the **Avail** column for your folder shows at least 10G,
- `Docker version 2x.x.x`,
- `Docker Compose version v2.20` or higher.

**If not.** `docker: command not found` means Docker is not installed: on a NAS, install it from the vendor's
app centre (look for "Docker" or "Container Manager"). Less than 2 GB of memory, or no way to install Docker,
means this machine is not suitable. Stop here and ask for help.

### 2.2 Decide who looks after it

Someone has to run the updates and, if needed, the restore. Pick that person now. Updates do not
happen by themselves (that is deliberate: nothing outside can connect into the machine), so the machine's
caretaker needs to run one command now and then.

**Do.** Write down who that is. If that person will work from their own computer instead of sitting at the
machine, they need a way to open a terminal on it from afar (SSH). Testing it is optional: in a terminal on
their computer run `ssh user@host docker ps` (with the real user and machine name) and look for a table
of containers, or an empty one.

**You should see.** A header line starting with `CONTAINER ID`, even if nothing is listed below it.

**If not.** `Permission denied` or `Connection refused`: SSH is off or the user is wrong. Skip this; you can
always do everything on the machine itself.

### 2.3 Buy the domain and add it to Cloudflare

**Do.**

1. Create a [Cloudflare](https://dash.cloudflare.com/sign-up) account. If you have a shared or role-based
   mailbox (not one person's private mail), use that. Turn on **two-factor authentication** in the profile
   settings: this account will control the way into the machine.
2. Buy a domain, about EUR 10 a year. **Cloudflare Registrar** is the simplest, as nothing else is needed. If it
   does not sell the ending you want, buy the domain elsewhere, add it to Cloudflare (look for "Add a domain") and
   change the nameservers at the seller to the two names Cloudflare shows you. Choose a name that does not reveal where
   the machine is.
3. Add to your private note: `PUBLIC_URL=https://lineup.example.com`, with your own domain and **no slash at the
   end**.

**You should see.** Your domain listed in the Cloudflare dashboard with the status **Active**.

**If not.** If it says "Pending nameserver update" after a bought-elsewhere domain, the nameserver change at the seller
has not taken effect yet. It can take up to a day; carry on with the other steps meanwhile.

### 2.4 Create the tunnel

**Do.**

1. In the Cloudflare dashboard open **Zero Trust** and choose the **Free** plan. Some people report that it asks for a card
   even on Free. If so, nothing should be charged on the Free plan: check this on the page before you confirm.
2. Go to **Networks → Tunnels → Create a tunnel**, choose the type **Cloudflared**, and name it `lineup`.
3. The page shows an install command with a long text after `--token`. Copy **only that long text** (the token) and add
   it to your private note as `TUNNEL_TOKEN=<the long text>`. **Do not run that command**: Lineup starts the tunnel by itself.
4. Add a **Public hostname**: your domain, with **no subdomain and no path**. Set the service type to `HTTP` and the URL to
   `web:8080`.
5. Open the settings of the domain itself and turn **off** these four, because they add scripts to the pages or block
   the app's own traffic: **Web Analytics**, **Rocket Loader**, **Email Address Obfuscation** and **Bot Fight Mode**.
   Turn **on** **Always Use HTTPS**.

**You should see.** The tunnel in the list, with the status **Inactive** or "Down". That is expected: nothing is
connected to it until the install.

**If not.** If you cannot find "Zero Trust", look for "Networks" or "Tunnels" in the left menu, or search the
dashboard for "tunnel".

**Keep analytics and tracking off.** Lineup itself uses no cookies, no analytics, no trackers and no
outside fonts or scripts, and that is on purpose: it keeps the app free of consent banners and keeps people's visits
private. Please keep it that way. Do not switch on Cloudflare Web Analytics (or any similar "insights" or
"analytics" feature), do not add Google Analytics or any tracking script to the page, and do not use a Cloudflare
feature that rewrites pages (Rocket Loader, Email Address Obfuscation, Zaraz). If a dashboard offers to switch one
on for you "to help", the answer is no.

### 2.5 Create the Google sign-in

People sign in with Google. Google needs to know your site, and it lets you say which accounts may use it.

Make a **new** Google Cloud project for this, not one you use for something else. The list of allowed people
belongs to the project.

**Do.**

1. Open the [Google Cloud console](https://console.cloud.google.com/) and create a **New project**, for example
   `lineup-selfhost`.
2. Find **Google Auth Platform → Audience**. Choose the type **External** and the publishing status **Testing**.
   Under **Test users** add every person who may sign in, by their Google e-mail address. Only these accounts can
   get in.
3. Find **Data access** and make sure that only `openid`, `email` and `profile` are selected.
4. Find **Clients → Create client** and choose **Web application**. Set:
   - Authorized JavaScript origin: `https://lineup.example.com`
   - Authorized redirect URI: `https://lineup.example.com/auth/v1/callback`

   (with your own domain, typed exactly, no slash at the end of the first one).
5. Google then shows a client id and a client secret. Add them to your private note as
   `GOOGLE_CLIENT_ID=<the id>` and `GOOGLE_SECRET=<the secret>`.

**You should see.** The client listed, and your people listed under Test users.

**If not.** If the console asks you to configure a "consent screen" or "branding" first, fill in the app name (for
example `Lineup`) and your own e-mail address as the support contact, then go back to step 4.

### 2.6 Read and accept the backup limits

Nothing to click here, but it is a decision that is yours. Read this and make sure you accept it:

> Backups run every night and are kept for 30 days, in a folder on this same machine. They are **not
> encrypted**, and anyone with access to this machine can read them. They protect against mistakes and bad
> updates. **If this machine is lost or fails, all data is lost**, unless someone has copied the backup folder
> elsewhere by hand. Also save the `.env` file somewhere safe and private: without it a restore on a new machine
> means everyone's sign-in and database passwords must be set up again.

If the machine has a second disk, or a folder on another device (a network share), choose a folder there for the
backups and add `BACKUP_DIR=/path/to/that/folder` to your private note. If you do not, backups go to a folder
called `backups` next to Lineup, which is fine to start with.

**You should see.** Nothing: this is a decision, not an action. The installer will show the same text and ask you to
type a word to confirm.

**If not.** If you are not comfortable with these limits, stop here. Copying the backup folder elsewhere by hand
(section 8) makes it much safer.

**Ready?** You should now have these in your private note: `PUBLIC_URL`, `TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_SECRET` and, if you chose one, `BACKUP_DIR`.

---

## 3. Install

You do this **on the machine**, in a terminal.

### 3.1 Get Lineup onto the machine

**Do.** Open the [releases page](https://github.com/LasterBergamot/lineup/releases), find the newest release, and
note its version, such as `v0.2.0`. Then, in the terminal, run these four commands one after another,
replacing both `v0.2.0` with that version:

```bash
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz.sha256
sha256sum -c selfhost-v0.2.0.tar.gz.sha256
tar -xzf selfhost-v0.2.0.tar.gz
```

**You should see.** After the third command: `selfhost-v0.2.0.tar.gz: OK`. That means the download is complete and
unchanged. The fourth command prints nothing and creates a folder named `selfhost`.

**If not.** `FAILED` means the download is damaged or has been tampered with: delete the two files and start again,
and do not go on. `curl: command not found`: use `wget` in place of `curl -LO`. A "not found" page: the version is
wrong, or that release has no `selfhost` file yet; try the previous release.

### 3.2 Check the machine once more

**Do.**

```bash
cd selfhost
./lineup.sh doctor
```

**You should see.** A list of checks, each marked OK, warning or problem. A warning (for example, little free disk) is
worth reading but does not stop you. Each problem comes with a line that says how to fix it.

**If not.** `Permission denied`: run `chmod +x lineup.sh` and try again. Fix every **problem** before going on.

### 3.3 Run the installer

**Do.** Have your private note open, and run:

```bash
./lineup.sh install
```

The installer asks, one by one: the public address (`https://lineup.example.com`, which must start with `https://`
and have no path), the tunnel token, the Google client id, the Google client secret and the backup folder. Paste
each from your note. For the secret, **nothing appears while you paste**: that is normal, it is hidden on purpose.
Then it shows the backup limits from section 2.6 and asks you to type `YES` (in Hungarian, `IGEN`). The installer
speaks Hungarian by default; if it offers a choice of language, choose English.

**You should see.** The installer creating passwords for itself (it never shows them), starting everything, and then
a message that Lineup is running, with the address and a reminder of what to save. It takes a few minutes the first
time, because it downloads the program parts.

**If not.**

- "A `.env` file already exists": this is a safety check. The installer will not overwrite the existing settings, as that
  would lock Lineup out of its own database. If this is a fresh install, you ran it before; use section 7 (update)
  instead.
- A value is rejected: read the message. The usual cause is an address without `https://`, or with a slash at the end.
- The installer stops with a message: read it, fix what it says and run `./lineup.sh install` again, unless it created
  the `.env` file, in which case it says what to do.

### 3.4 Save the `.env` file

The installer wrote a file called `.env` in the folder you are in. It holds every password Lineup needs. It is **not**
stored anywhere else.

**Do.** Copy that file to a safe, private place that is **not on this machine**: a password manager that stores files, or an
encrypted USB stick. The name starts with a dot, so file managers hide it: look for "show hidden files". Do not
e-mail it and do not put it in a shared folder.

**You should see.** The file safely stored elsewhere.

**If not.** If you cannot find it, in the terminal run `ls -a` in the Lineup folder: the file named `.env` is in
the list.

---

## 4. Check it works

**Do.**

1. In the terminal, run `./lineup.sh status`.
2. On any computer or phone, open `https://lineup.example.com` (your own domain).
3. Press the sign-in button and sign in with a Google account that is on the test-user list.

**You should see.**

1. A list of containers all shown as running, a line saying the app is healthy, the age of the last backup (there is none
   yet on the first day), the free disk and the current version.
2. The Lineup start page.
3. After signing in, you are back in Lineup and can create a team.

**If not.**

- The status shows a problem: read the line, then see [section 10](#10-when-something-is-wrong).
- The page does not open: wait two minutes (the tunnel needs a moment), then see section 10, "The site is
  unreachable".
- Google says **access blocked**: the account is not on the test-user list. See section 5.

---

## 5. Add or remove a person

Who may sign in is decided by Google's list of test users, not by Lineup.

**Do.**

1. Open the [Google Cloud console](https://console.cloud.google.com/) and select your Lineup project.
2. Go to **Google Auth Platform → Audience → Test users**.
3. To add a person, choose **Add users** and type their Google e-mail address. To remove a person, remove their
   address from the list. Save.
4. Once someone can sign in, they join a team in Lineup with an invite link, made by a member of the team in the app.

**You should see.** The new address in the list. The person can now sign in.

**If not.** If the person still sees **access blocked**, check that they use exactly that Google account (not another one
signed in on the same browser), and wait a minute.

Removing a person from the list stops them signing in again, but does not delete their data from Lineup. If someone
asks for their data to be deleted or exported, that is a separate job with its own rules: see [[Privacy and Security]].

---

## 6. Everyday

Nothing needs doing every day. Backups run by themselves at night, and Lineup restarts by itself when the machine does.

**Once a month**, open a terminal on the machine, go to the Lineup folder and run:

```bash
./lineup.sh status
```

Check three things: the app is healthy, the last backup is **less than a day and a half old**, and there is free disk
left. The status also says whether a newer version of Lineup exists. Updates do not install by themselves: when a new version
exists, schedule an update (section 7).

**You should see.** A healthy app and a recent backup.

**If not.** See [section 10](#10-when-something-is-wrong).

---

## 7. Update

**Do.** Pick a quiet time (the app is briefly unavailable), open a terminal on the machine, go to the Lineup folder and
run:

```bash
./lineup.sh update
```

It does these things by itself, and tells you as it goes: finds the newest version, downloads it and checks that it
is intact, **takes a backup first** (and stops if the backup fails, so there is never an update without a fresh
backup), installs the new version and checks that it works.

To go to a specific version instead, add it: `./lineup.sh update --version v0.2.0`.

**You should see.** A message that Lineup is now on the new version and healthy. Run `./lineup.sh status` afterwards.

**If not.** If the update fails, the script tells you exactly what happened. There are two cases:

- It says the update was **undone and nothing was lost**: Lineup is on the old version again. Wait a day, or ask for help
  with the message.
- It says the **database was changed**: it does not guess. Follow the instruction in the message: it names a restore
  command that goes back to the backup from just before the update (section 9).

Do not improvise. If neither message is shown, ask for help.

Developers can run the same update from their own computer; see [[Self-Hosting Reference]].

---

## 8. Backups

Read this part carefully. It says what the backups can and cannot do.

> Backups run every night and are kept for 30 days, in a folder on this same machine. They are **not
> encrypted**, and anyone with access to this machine can read them. They protect against mistakes and bad
> updates. **If this machine is lost or fails, all data is lost**, unless someone has copied the backup folder
> elsewhere by hand. Also save the `.env` file somewhere safe and private: without it a restore on a new machine
> means everyone's sign-in and database passwords must be set up again.

In plain words: backups help when someone deletes something by mistake, or an update goes wrong. They do not help if
the machine is stolen, burns, or its disk breaks, because the backups are on the same machine. To be safe against that,
**copy the backup folder to another place by hand** now and then, for example once a month.

Two details that are good to know. The backups leave out people's sign-in sessions, so if you ever restore, everyone
simply has to sign in again, and a stolen backup cannot be used to take over a signed-in session. Backups older than 30
days are deleted by themselves.

**Take a backup now.** Run `./lineup.sh backup`. It lists the files it made and their size.

**Copy the folder elsewhere by hand.**

1. Find the folder: it is `BACKUP_DIR` from your note, or the folder called `backups` inside the Lineup folder.
2. Copy the whole folder to a USB drive, another computer, or a different device. On a NAS you can usually do this
   with the file manager (copy the folder to another share or disk). From another computer with SSH, one way is
   `scp -r user@host:/path/to/backups ./lineup-backups` (with the real user, machine and path). The backups are not
   encrypted, so keep the copy somewhere private.
3. In the folder, you will see two files per night, named like `lineup-2026-11-04.dump` and `auth-2026-11-04.dump`
   (one for the data, one for the sign-in accounts), and a small file `last-success` holding the time of the last good
   backup. Always copy all of them.

**You should see.** The copy next to the original, with the same files.

**If not.** If the copy is much smaller than the original or some files are missing, the copy was interrupted: do it
again.

---

## 9. Restore

Restoring puts the data back to the state of an earlier night. Use it after a mistake you cannot fix any other way, or when
the update message tells you to.

**Before you do it, know this:** everything entered **after** that date is **lost**, and **everyone has to sign in again**.

**Do.** In a terminal on the machine, in the Lineup folder:

```bash
./lineup.sh restore
```

It lists the dates that have a backup. To choose one directly: `./lineup.sh restore --date 2026-11-03` (use a date from
the list). It warns you again and asks you to type `RESTORE` (in Hungarian, `VISSZAALLIT`). It then takes a **safety backup of
the current state first** (so even a mistaken restore can be undone), stops the app, puts the data back, starts
everything and checks that it works.

**You should see.** A message that the restore finished and Lineup is healthy. Open the address and sign in again.

**If not.** If the restore stops with a message, follow it. The safety backup means nothing is lost by trying again. If the
whole machine is gone, restoring onto a new machine needs the backup folder **and** the saved `.env` file (section 3.4):
ask for help with that.

---

## 10. When something is wrong

| What you see | What to do | When to ask for help |
|---|---|---|
| **The site is unreachable** (the page does not open) | Is the machine switched on and connected to the network? Run `./lineup.sh status`: are the containers running? In the Cloudflare dashboard open **Networks → Tunnels**: is `lineup` shown as healthy or connected? If it is down, restart the machine (Lineup starts again by itself) and wait a few minutes | The machine is on, everything is running and the tunnel is connected, but the page still does not open; or the tunnel token was changed |
| **Sign-in says "access blocked"** (or "this app is not verified" with no way forward) | The account is not on the test-user list. Add it (section 5) | The account is on the list and it still fails after a few minutes |
| **Google shows an error with `redirect_uri_mismatch`** | In the Google Cloud console, **Clients**, check that the redirect URI is exactly `https://lineup.example.com/auth/v1/callback` with your domain (section 2.5) | It matches exactly and still fails |
| **Sign-in works, but you land on a blank page or an error page** | Run `./lineup.sh status`. If a container is not healthy, wait a minute and look again | It stays unhealthy after five minutes |
| **`status` says the last backup is more than a day and a half old** | Run `./lineup.sh backup` and read what it says. Check the free disk with `./lineup.sh status` | The backup fails, or disk space is nearly full |
| **Disk is almost full** | Free some space on the machine, or move old backups elsewhere (copy first, then delete) | You are not sure what is safe to delete: do not delete the Lineup folder or its `.env` |
| **An update failed** | Do exactly what the message says (undone, or restore command) | The message is not shown or you do not understand it |
| **A PDF does not download, or takes a long time** | Wait a minute and try again. Very rarely, many people create PDFs at once | It keeps failing |
| **After a restore, nobody is signed in** | This is expected. Everyone signs in again | It does not work after signing in again |

**Asking for help.** Say what you did, what you saw, and copy the exact message. Never send anyone your `.env` file, your
tunnel token or your Google client secret, and never post them in a public place: they give full access. If you suspect
one of them leaked, that is a data breach: follow the [[Breach Runbook]].
