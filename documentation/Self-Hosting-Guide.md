# Self-Hosting Guide

How to run your own copy of Lineup on one always-on machine (a NAS or a small server), step by step,
written for people who have never used a terminal. The Hungarian version, with the same steps in the
same order, is [[Saját gépes telepítés]]. Developers who want the architecture and the details should read
[[Self Hosting Reference]].

This guide uses `lineup.example.com` everywhere as an example. Wherever you see it, type **your own address**. If you bought the domain `myteam.com`, your address is `https://myteam.com` (no `lineup.` in front, and no slash at the end).

If a step says "ask for help", ask the person who gave you this guide. If there is nobody, open an issue on the project's GitHub page and describe what you did and what you saw; never include a password, token or secret.

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
The machine does not open any door to the internet, and you do not need to change anything on your router: the connection goes through a service called a tunnel (explained below), which is what keeps the machine hidden and safe.

**How long it takes.** Set aside about an hour for the first setup (plus, sometimes, a wait of up to a day for a newly bought domain to become active, see step 2.3). Most of it is creating accounts
and copying values from one web page to another. After that, the daily work is nothing, and an update takes a
few minutes.

**What it costs.** The domain, about EUR 10 a year. The Cloudflare and Google parts are free, and
Lineup itself is free. The machine and its electricity are yours.

**Who should do the first setup.** Someone careful, not necessarily technical: you will create accounts, copy
values exactly and type a few commands. If you can follow a recipe, you can do this. Doing it with a second
person reading the steps aloud helps.

**Words you will meet.** Each one is explained once here:

- **Terminal**: a window where you type a command and press Enter instead of clicking. Every command in this guide is shown in a grey box or between backticks: copy it exactly. Section 2.1 shows how to open one.
- **SSH**: a way to open a terminal on another machine from your own computer, over the network. Copying and pasting works better this way.
- **Docker**: a program that runs other programs in sealed boxes (called containers), so they do not
  interfere with the machine. Lineup is delivered as a set of such boxes. You only need to know that Docker has to
  be installed and running.
- **Domain**: the name of a website, such as `lineup.example.com`. You buy it once a year.
- **Tunnel**: a private pipe from the machine to Cloudflare (a company that runs part of the internet).
  Visitors go to Cloudflare, Cloudflare passes the request through the pipe to your machine. Because the
  machine calls out to Cloudflare, nobody has to be able to call in.
- **`.env` file**: a hidden settings file that the installer creates on the machine. It holds every password Lineup needs. You will save a copy of it in step 3.4.
- **Client id, client secret and token**: long pieces of text that work like a user name and a password between two services (here: Google and Lineup, and Cloudflare and Lineup). Treat them like passwords.
- **Backup**: a copy of the data made so that a mistake or a failed update can be undone. How Lineup's backups
  work, and what they do **not** protect against, is in [section 8](#8-backups). Please read that section
  before you put real data in.

**One more thing before real people use it.** Running Lineup yourself does **not** take it out of the European data protection law (GDPR). Whoever runs it is responsible for the data of the people in it. Until the privacy checklist on
the wiki page *Privacy and Security* ([[Privacy and Security]], the section on self-hosted installs) is done, use only made-up names and data inside Lineup. The person who runs the install completes that checklist; signing in with a real Google account to try it out is fine.

**A note on wording.** Websites such as Cloudflare and Google change their menus often. This guide has no
screenshots for that reason. It names the buttons as they are at the time of writing; if you cannot find one,
**look for the closest wording**.

**Keep your values in one private note.** In the steps below you will collect a few values (an address, a
token, a client id). Keep them in one **secure note in a password manager** on your own computer, never in an e-mail or a chat. (On a Mac or Linux computer you can use a private text file instead: in a terminal run
`mkdir -p ~/.config/lineup && touch ~/.config/lineup/selfhost.env && chmod 600 ~/.config/lineup/selfhost.env`, and open it with any text editor.) Every `NAME=value` line in this guide goes into that note.

---

## 2. Before you start

Six things have to be ready before you install. They do not depend on each other much, so you can do them in
any order, but do all of them.

### 2.1 Check the machine

The machine needs to be switched on all the time, have Docker installed, at least 2 GB of memory (4 GB is
comfortable) and at least 10 GB of free disk.

**How to open a terminal on the machine.** The easiest way is from your own computer, with SSH. On a NAS, first look in its settings for "Terminal" or "SSH" and turn it on. Then:

- on Windows, open the Start menu, type `PowerShell` and press Enter; on a Mac press Cmd+Space, type `Terminal` and press Enter;
- type `ssh name@address` and press Enter, where `name` is the machine's administrator user name and `address` is the machine's network address (look in the NAS's own admin page, or in your router's list of devices);
- the first time, it asks "Are you sure you want to continue connecting?": type `yes`. Then it asks for the password: **nothing appears while you type it**, that is normal; press Enter;
- keep this window open for the whole guide. To paste into it, use right-click, or Ctrl+Shift+V (Cmd+V on a Mac).

If the machine has a screen and keyboard, or a terminal app of its own, you can use that instead.

Install into a folder with plenty of free space (on a NAS, a folder on the main data volume, not the small system disk). Go to that folder with `cd` and its path; the command below then checks **that** folder. If you are unsure, use your home folder: `cd ~`.

**Do.** In the terminal on the machine, copy this line, paste it and press Enter:

```bash
uname -m; grep MemTotal /proc/meminfo; df -h .; docker --version; docker compose version
```

**You should see.** Five or six lines:

- `x86_64` or `aarch64` (the kind of processor; either works),
- `MemTotal:` followed by a number of at least about 1900000 (that is kilobytes: roughly 2 GB),
- a small table: on its **last line**, the **Avail** column shows at least 10G (it may be written in M, G or T),
- `Docker version` followed by a number starting with 20 or higher,
- `Docker Compose version v2.20` or higher.

**If not.** `docker: command not found` means Docker is not installed: on a NAS, install it from the vendor's
app centre (look for "Docker" or "Container Manager"). A `permission denied` error about the Docker "socket" means your user is not allowed to use Docker: log in with the NAS administrator account, or put `sudo` in front of the command (and in front of every `./lineup.sh` command later). `'compose' is not a docker command`, or a Compose version older than 2.20: update Docker or Container Manager from the app centre. Less than 2 GB of memory, or no way to install Docker,
means this machine is not suitable. Stop here and ask for help.

### 2.2 Decide who looks after it

Someone has to run the updates and, if needed, the restore. Pick that person now (the machine's caretaker). Updates do not
happen by themselves (that is deliberate: nothing outside can connect into the machine), so the caretaker needs to run one command now and then. The caretaker also keeps the domain renewed (see 2.3).

**Do.** Write down who that is in your note. If that person will work from their own computer instead of sitting at the
machine, they need SSH (see 2.1). Testing it is optional: in a terminal on
their computer run `ssh name@address docker ps` (with the real user name and machine address) and look for a table
of containers, or an empty one. Skip this test if the caretaker will always sit at the machine.

**You should see.** A header line starting with `CONTAINER ID`, even if nothing is listed below it.

**If not.** `Connection refused`: SSH is off on the machine. `Permission denied (publickey,password)`: wrong user name or password. An error about the Docker socket: see the Docker note in 2.1. You can skip this test; you can always do everything on the machine itself.

### 2.3 Buy the domain and add it to Cloudflare

**Do.**

1. Create a [Cloudflare](https://dash.cloudflare.com/sign-up) account. If you have a shared mailbox (an address such as `office@yourclub.example`, not one person's private mail), use that. Turn on **two-factor authentication** (a code from your phone each time you sign in) in the profile
   settings: this account will control the way into the machine.
2. Buy a domain (a name like `myteam.com`), about EUR 10 a year, and turn on **auto-renew**: if the domain expires, the site silently stops working. Decide who pays and renews it. **Cloudflare Registrar** is the simplest, as nothing else is needed. If it
   does not sell the ending you want (such as `.com` or `.hu`), buy the domain elsewhere, add it to Cloudflare (look for "Add a domain") and
   change the nameservers at the seller to the two names Cloudflare shows you (they look like `xxx.ns.cloudflare.com`; you type them into the seller's DNS settings page). Choose a name that does not reveal where
   the machine is (no street or home town in it).
3. Add to your private note: `PUBLIC_URL=https://lineup.example.com`, with your own domain and **no slash at the
   end**.

**You should see.** Your domain listed in the Cloudflare dashboard with the status **Active**.

**If not.** If it says "Pending nameserver update" after a bought-elsewhere domain, the nameserver change at the seller
has not taken effect yet. It can take up to a day. You can do steps 1 to 3 of 2.4 meanwhile, but wait for **Active** before step 4 of 2.4 and before 2.5.

### 2.4 Create the tunnel

**Do.**

1. In the Cloudflare dashboard open **Zero Trust** and choose the **Free** plan. It may ask for a team name (any name will do). Some people report that it asks for a card
   even on Free. If so, nothing should be charged on the Free plan: check this on the page before you confirm.
2. Go to **Networks → Tunnels → Create a tunnel**, choose the type **Cloudflared**, and name it `lineup`.
3. The page shows an install command with a long text after `--token`. Copy **only that long text** (the token: it usually starts with `eyJ`, runs to the end of the command and has no spaces; any of the tabs shows it) and add
   it to your private note as `TUNNEL_TOKEN=<the long text>`. **Do not run that command**: Lineup starts the tunnel by itself.
4. Add a **Public hostname**: your domain, with **no subdomain and no path**. Set the service type to `HTTP` and the URL to
   `web:8080`. Type that **exactly**: it is not a typo and not a website, it is the internal name of Lineup's own web part.
5. Open the settings of the domain itself (in the main Cloudflare dashboard, not in Zero Trust: choose your domain, then look through its menus, such as Speed, Security, SSL/TLS and Web Analytics) and turn **off** these four, because they add scripts to the pages or block
   the app's own traffic: **Web Analytics**, **Rocket Loader**, **Email Address Obfuscation** and **Bot Fight Mode**.
   Turn **on** **Always Use HTTPS**. If a setting is already off, leave it.

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

1. Open the [Google Cloud console](https://console.cloud.google.com/) (sign in with a Google account; accept the terms if it asks; no card or billing is needed) and create a **New project**, for example
   `lineup-selfhost`. If the console shows a **Get started** page for Google Auth Platform (a short form for the app name and your e-mail, the "consent screen"), fill it in first: app name `Lineup`, your own e-mail as the contact.
2. Find **Google Auth Platform → Audience**. Choose the type **External** and the publishing status **Testing**.
   Under **Test users** add every person who may sign in, **including yourself**, by their Google e-mail address (it must be a Google account). Only these accounts can
   get in. "Testing" is the right status: it does not mean the app is unfinished, it is what keeps the list of allowed people in force.
3. Find **Data access** and make sure that only `openid`, `email` and `profile` are selected.
4. Find **Clients → Create client** and choose **Web application**. Set:
   - Authorized JavaScript origin: `https://lineup.example.com`
   - Authorized redirect URI: `https://lineup.example.com/auth/v1/callback`

   (with your own address, typed exactly, no slash at the end of the first one; they are two separate fields, each with an **Add URI** button).
5. Google then shows a client id and a client secret. **Copy the secret before you close the box**: it may not be shown again (if you lose it, create a new secret). Add them to your private note as
   `GOOGLE_CLIENT_ID=<the id>` and `GOOGLE_SECRET=<the secret>`.

**You should see.** The client listed, and your people listed under Test users.

**If not.** If you cannot find **Audience** or **Clients**, you probably have not finished the **Get started** form (step 1): finish it, then look again. Look for the closest wording; Google renames these menus now and then.

### 2.6 Read and accept the backup limits

Nothing to click here, but it is a decision that is yours. Read this and make sure you accept it:

> Backups run every night and are kept for 30 days, in a folder on this same machine. They are **not
> encrypted**, and anyone with access to this machine can read them. They protect against mistakes and bad
> updates. **If this machine is lost or fails, all data is lost**, unless someone has copied the backup folder
> elsewhere by hand. Also save the `.env` file somewhere safe and private: without it a restore on a new machine
> means everyone's sign-in and database passwords must be set up again.

(The `.env` file is the hidden settings file the installer creates; you will save it in step 3.4.)

If the machine has a second disk, or a folder on another device (a network share), choose a folder there for the
backups and add `BACKUP_DIR=/path/to/that/folder` to your private note (an example path on a NAS: `/volume1/backup`; to see the disks, type `ls /` or `ls /volume1`). If you do not, leave it empty: when the installer asks for the backup folder, just press Enter, and backups go to a folder called `backups` inside the Lineup folder, which is fine to start with.

**You should see.** Nothing: this is a decision, not an action. The installer will show the same text and ask you to
type a word to confirm.

**If not.** If you are not comfortable with these limits, stop here. Copying the backup folder elsewhere by hand
(section 8) makes it much safer.

**Ready?** You should now have these in your private note: `PUBLIC_URL`, `TUNNEL_TOKEN`, `GOOGLE_CLIENT_ID`,
`GOOGLE_SECRET` and, if you chose one, `BACKUP_DIR`.

---

## 3. Install

You do this **on the machine**, in a terminal (see 2.1), in the folder you chose for it (`cd` to it first, or `cd ~` for your home folder).

### 3.1 Get Lineup onto the machine

**Do.** Open the [releases page](https://github.com/LasterBergamot/lineup/releases), find the newest release, and
note its version, such as `v0.2.0`. (Look for the one labelled **Latest**; do not use one marked **Pre-release**.) Then, in the terminal, run these four commands one at a time (press Enter after each), replacing `v0.2.0` with that version in **all seven places**:

```bash
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz
curl -LO https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz.sha256
sha256sum -c selfhost-v0.2.0.tar.gz.sha256
tar -xzf selfhost-v0.2.0.tar.gz
```

**You should see.** After the third command: `selfhost-v0.2.0.tar.gz: OK`. (That command checks, with a fingerprint, that the file is complete and unchanged.) That means the download is complete and
unchanged. The fourth command prints nothing and creates a folder named `selfhost`.

**If not.** `FAILED` means the download is damaged or has been tampered with: delete the two files (`rm selfhost-v0.2.0.tar.gz selfhost-v0.2.0.tar.gz.sha256`) and start again,
and do not go on. `curl: command not found`: use `wget` in place of `curl -LO` (for example `wget https://github.com/LasterBergamot/lineup/releases/download/v0.2.0/selfhost-v0.2.0.tar.gz`). A "not found" page: the version is
wrong, or that release has no `selfhost` file yet; try the previous release.

### 3.2 Check the machine once more

**Do.**

```bash
cd selfhost
pwd
./lineup.sh doctor
```

`pwd` prints the full path of the **selfhost folder**, the Lineup folder from now on. Write it in your note as `LINEUP_DIR=<that path>`: every later section starts with `cd` to it. (`doctor` is a read-only health check; it changes nothing.)

**You should see.** A list of checks, each marked OK, warning or problem. A warning (for example, little free disk) is
worth reading but does not stop you. Each problem comes with a line that says how to fix it.

**If not.** `No such file or directory`: you are not in the right folder; `cd` to it first. `Permission denied`: run `chmod +x lineup.sh` and try again (if the message is about Docker, see 2.1). Fix every **problem** before going on.

### 3.3 Run the installer

**Do.** Have your private note open, and run:

```bash
./lineup.sh install
```

The installer asks, one by one: the public address (`https://lineup.example.com`, which must start with `https://`
and have no path), the tunnel token, the Google client id, the Google client secret and the backup folder. Paste
each from your note (right-click, or Ctrl+Shift+V; Cmd+V on a Mac). For the secret, **nothing appears while you paste**: that is normal, it is hidden on purpose.
Then it shows the backup limits from section 2.6 and asks you to type `YES` (in Hungarian, `IGEN`; if you see Hungarian, type `IGEN`). The installer
speaks Hungarian by default; if it offers a choice of language, choose English.

**You should see.** The installer creating passwords for itself (it never shows them), starting everything, and then
a message that Lineup is running, with the address and a reminder of what to save. It takes a few minutes the first
time, because it downloads the program parts. Do not close the window meanwhile; if the connection drops, run `./lineup.sh status` and then ask for help.

**If not.**

- "A `.env` file already exists": this is a safety check. The installer will not overwrite the existing settings, as that
  would lock Lineup out of its own database. If Lineup was installed here before, use section 7 (update) instead. If you believe this is a first install, an earlier attempt left the file behind: do not delete anything, ask for help.
- You typed a value wrong and only noticed after the install finished (a wrong token, secret or address): ask for help; it can be corrected, but not by running the installer again.
- A value is rejected: read the message. The usual cause is an address without `https://`, or with a slash at the end.
- The installer stops with a message: read it, fix what it says and run `./lineup.sh install` again, unless it created
  the `.env` file, in which case it says what to do.

### 3.4 Save the `.env` file

The installer wrote a file called `.env` in the folder you are in. It holds every password Lineup needs. It is **not**
stored anywhere else.

**Do.** Copy that file to a safe, private place that is **not on this machine**: a password manager that stores files (as an attachment to a secure note), or a USB stick kept somewhere private. The name starts with a dot, so file managers hide it: in the NAS's file manager look for "show hidden files", then download the file; or, from your own computer, `scp name@address:/path/to/selfhost/.env .` (using the path that `pwd` printed). Do not
e-mail it and do not put it in a folder that other people of the NAS can open.

**You should see.** The file safely stored elsewhere. Open the copy and check it is not empty (about 20 lines).

**If not.** If you cannot find it, in the terminal run `ls -a` in the Lineup folder: the file named `.env` is in
the list.

---

## 4. Check it works

**Do.**

1. In the terminal, go to the selfhost folder (`cd` to the path in your note), run `./lineup.sh backup` once (it makes the first backup), then `./lineup.sh status`.
2. On any computer or phone, open `https://lineup.example.com` (your own domain).
3. Press the sign-in button on the start page and sign in with a Google account that is on the test-user list. Google may show a warning page saying it has not verified the app: that is expected for a test app; choose **Advanced**, then continue to the app.

**You should see.**

1. A list of containers all shown as running, a line saying the app is healthy, the age of the last backup (a few minutes, after the backup you just made), the free disk and the current version.
2. The Lineup start page.
3. After signing in, you are back in Lineup and can create a team (the app asks you to when you have none).

**If not.**

- `No such file or directory`: wrong folder, `cd` to the selfhost folder first.
- The status shows a problem: read the line, then see [section 10](#10-when-something-is-wrong).
- The page does not open: wait two minutes (the tunnel needs a moment), then see section 10, "The site is
  unreachable".
- Google says **access blocked**: the account is not on the test-user list. See section 5.

---

## 5. Add or remove a person

Who may sign in is decided by Google's list of test users, not by Lineup.

**Do.**

1. Open the [Google Cloud console](https://console.cloud.google.com/) and select your Lineup project (the project name at the top, for example `lineup-selfhost`).
2. Go to **Google Auth Platform → Audience → Test users**.
3. To add a person, choose **Add users** and type their Google e-mail address. To remove a person, remove their
   address from the list. Save.
4. Once someone can sign in, they join a team in Lineup with an invite link, made by a member of the team on the team's page in the app and sent to the person.

**You should see.** The new address in the list. The person can now sign in.

**If not.** If the person still sees **access blocked**, check that they use exactly that Google account (not another one
signed in on the same browser), and wait a minute.

Removing a person from the list stops them signing in again, but does not delete their data from Lineup. If someone
asks for their data to be deleted or exported, that is a separate job with its own rules: see [[Privacy and Security]].

---

## 6. Everyday

Nothing needs doing every day. Backups run by themselves at night, and Lineup restarts by itself when the machine does.

**Once a month** (put a reminder in your calendar), open a terminal on the machine, go to the selfhost folder (`cd` to the path in your note) and run:

```bash
./lineup.sh status
```

Check three things: the app is healthy, the last backup is **less than a day and a half old**, and there is free disk
left (at least 5 GB). The status also says whether a newer version of Lineup exists. Updates do not install by themselves: when a new version
exists, schedule an update (section 7), at the latest within a few months. If the machine lost power, Lineup starts again by itself; `status` confirms it.

**You should see.** A healthy app and a recent backup.

**If not.** See [section 10](#10-when-something-is-wrong).

---

## 7. Update

**Do.** Pick a quiet time (the app is briefly unavailable), open a terminal on the machine, go to the selfhost folder (`cd` to the path in your note) and
run (you do not download anything yourself; the update does that):

```bash
./lineup.sh update
```

It does these things by itself, and tells you as it goes: finds the newest version, downloads it and checks that it
is intact, **takes a backup first** (and stops if the backup fails, so there is never an update without a fresh
backup), installs the new version and checks that it works.

Do not close the window while it runs. To go to a specific version instead, add it: `./lineup.sh update --version v0.2.0`.

**You should see.** A message that Lineup is now on the new version and healthy. Run `./lineup.sh status` afterwards.

**If not.** If the update fails, the script tells you exactly what happened. There are two cases:

- It says the update was **undone and nothing was lost**: Lineup is on the old version again. Ask for help, quoting the message, before you try again.
- It says the **database was changed**: it does not guess. Follow the instruction in the message: it names a restore
  command that goes back to the backup from just before the update (section 9).

Do not improvise. If neither message is shown, ask for help.

Developers can run the same update from their own computer; see [[Self Hosting Reference]].

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

Two more details. The backups leave out people's sign-in sessions, so if you ever restore, everyone
simply has to sign in again, and a stolen backup cannot be used to take over a signed-in session. Backups older than 30
days are deleted by themselves.

**Take a backup now.** Run `./lineup.sh backup`. It lists the files it made and their size.

**Copy the folder elsewhere by hand.**

1. Find the folder: it is `BACKUP_DIR` from your note, or the folder called `backups` inside the selfhost folder.
2. Copy the whole folder to a USB drive, another computer, or a different device. On a NAS you can usually do this
   with the file manager (copy the folder to another share or disk). Optionally, from another computer with SSH, one way is
   `scp -r user@host:/path/to/backups ./lineup-backups` (with the real user, machine and path). The backups are not
   encrypted, so keep the copy somewhere private, for example a USB stick in a locked drawer.
3. In the folder, you will see two files per night, named like `lineup-2026-11-04.dump` and `auth-2026-11-04.dump`
   (one for the data, one for the sign-in accounts), and a small file `last-success` holding the time of the last good
   backup. Always copy all of them.

**You should see.** The copy next to the original, with the same files.

**If not.** If the number of files or the total size (see the folder's properties) differs from the original, the copy was interrupted: do it
again.

Before real data goes in, try a restore once (section 9) so you know it works.

---

## 9. Restore

Restoring puts the data back to the state of an earlier night. Use it after a mistake you cannot fix any other way, or when
the update message tells you to.

**Before you do it, know this:** everything entered **after** that date is **lost**, and **everyone has to sign in again**.

**Do.** In a terminal on the machine, in the selfhost folder (`cd` to the path in your note):

```bash
./lineup.sh restore
```

It lists the dates that have a backup and asks which one to use (type the date, such as 2026-11-03). To choose one directly: `./lineup.sh restore --date 2026-11-03` (use a date from
the list). It warns you again and asks you to type `RESTORE` (in Hungarian, `VISSZAALLIT`). It then takes a **safety backup of
the current state first** (so even a mistaken restore can be undone), stops the app, puts the data back, starts
everything and checks that it works.

**You should see.** A message that the restore finished and Lineup is healthy. Open the address and sign in again.

**If not.** If the restore stops with a message, follow it. The safety backup means nothing is lost by trying again. If the
whole machine is gone, restoring onto a new machine needs the backup folder **and** the saved `.env` file (section 3.4):
ask for help with that; the steps are in the technical page [[Self Hosting Reference]] (the section on backups and restore).

---

## 10. When something is wrong

| What you see | What to do | When to ask for help |
|---|---|---|
| **`./lineup.sh: No such file or directory`** | You are in the wrong folder: `cd` to the selfhost folder (the path from your note) | You cannot find the folder |
| **Docker says "permission denied"** | Use the administrator account, or put `sudo` in front of the command (section 2.1) | It still fails |
| **The site is unreachable** (the page does not open) | Is the machine switched on and connected to the network? Run `./lineup.sh status`: are the containers running? In the Cloudflare dashboard open **Networks → Tunnels**: is `lineup` shown as **Healthy** (green)? If it is down, restart the machine (use the NAS's own web page and choose Restart; Lineup starts again by itself) and wait a few minutes | The machine is on, everything is running and the tunnel is connected, but the page still does not open; or the tunnel token was changed |
| **Sign-in says "access blocked"** (or "this app is not verified" with no way forward) | The account is not on the test-user list. Add it (section 5) | The account is on the list and it still fails after a few minutes |
| **Google shows an error with `redirect_uri_mismatch`** | In the Google Cloud console, **Clients**, check that the redirect URI is exactly `https://lineup.example.com/auth/v1/callback` with your address (section 2.5; in the Google Cloud console look for your project's **Clients** page) | It matches exactly and still fails |
| **Sign-in works, but you land on a blank page or an error page** | Run `./lineup.sh status`. If a container is not healthy, wait a minute and look again | It stays unhealthy after five minutes |
| **`status` says the last backup is more than a day and a half old** | Run `./lineup.sh backup` and read what it says. Check the free disk with `./lineup.sh status` | The backup fails, or disk space is nearly full |
| **Disk is almost full** | Free some space on the machine, or move old backups elsewhere (copy first, then delete) | You are not sure what is safe to delete: do not delete the Lineup folder or its `.env` |
| **An update failed** | Do exactly what the message says (undone, or restore command) | The message is not shown or you do not understand it |
| **A PDF does not download, or takes a long time** | Wait a minute and try again. Very rarely, many people create PDFs at once | It keeps failing |
| **The site worked and suddenly says the domain is unavailable** | The domain may have expired: check its renewal (section 2.3) | You cannot renew it |
| **After a restore, nobody is signed in** | This is expected. Everyone signs in again | It does not work after signing in again |

**Asking for help.** Say what you did, what you saw, and copy the exact message. Never send anyone your `.env` file, your
tunnel token or your Google client secret, and never post them in a public place: they give full access. If you suspect
one of them leaked, that is a data breach: follow the [[Breach Runbook]].
