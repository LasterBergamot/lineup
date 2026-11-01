# Supabase Admin Guide

How to fix or remove data on the **dev** Supabase project by hand with Supabase's web client
(*Studio*): a stuck invitation, a team that should go, or a person's data on request. Read it before
you open the SQL editor. Menu names change now and then, so follow the intent if a label differs.

> **Status:** written from the schema and migrations in the repo. The click paths and the SQL have
> not yet been walked through once on the dev project (#179's last acceptance step). The first
> person to do so should fix whatever the UI shows differently and delete this note.

## Why this is risky

Studio runs your queries as the **`postgres` role**, the owner of every table. Row Level Security
(RLS) does not apply to it, and nothing in the app checks what you do: no team scoping, no
"last owner" rule, no audit log. The API's role, `lineup_app`, is the opposite: it cannot see
`auth.users` or `alembic_version` and cannot change the schema (migrations
`8b1f3c2d9a47`, `c4e7a1b2d905`). So admin work has to happen here, and a wrong `DELETE` is
permanent: the Free plan has **no backups** ([[Privacy and Security]], section 7).

**Never**

- turn RLS off on a table, or add a policy to "make something work" (the API would then depend on
  a state the migrations don't describe; fix it with a migration instead);
- run changes as `lineup_app` (don't paste its password into Studio or `psql`): it is the app's
  identity, not an admin tool;
- change the schema by hand (`ALTER TABLE`, new tables, the `alembic_version` table): use
  `task migrate-new`, or Alembic stops matching the database;
- run a `DELETE` or `UPDATE` without a `WHERE` clause, or without having run the same `WHERE` as a
  `SELECT` first;
- skip the backup in section 6 before a destructive change.

## 1. Sign in to the project

1. Open [supabase.com/dashboard](https://supabase.com/dashboard) and sign in with the account that
   owns the organisation (the owner's GitHub or e-mail login, not a Lineup user).
2. Pick the dev project (the `<project-ref>` in `https://<project-ref>.supabase.co`, the same
   project that [[Auth Setup]] configures).
3. You now have two tools in the left sidebar:
   - **Table Editor**: a spreadsheet view of one table. Good for looking at rows and for deleting
     a single row.
   - **SQL Editor**: type a query, press **Run**. Needed for joins, `auth.users` and anything
     that touches more than one row.
   - **Authentication → Users**: the sign-in accounts (see section 3).

In the Table Editor make sure the schema selector (top left) says **`public`**. The app's tables
live there: `teams`, `team_members`, `team_invitations`, `players`, `saved_lineups`,
`lineup_player_snapshots` (and `alembic_version`, which you leave alone).

## 2. What is connected to what

Deleting a row also affects rows that point at it. The foreign keys decide how:

| Delete this | These rows follow or block | Why |
|-------------|---------------------------|-----|
| A **team** | **Blocked** (`RESTRICT`) while it still has `players` or `saved_lineups`. Its `team_members` and `team_invitations` are **deleted with it** (`CASCADE`). Other lineups that merely *name* it as `source_team_id` / `source_opponent_id` keep existing, those columns become `NULL` (`SET NULL`) | A team is a workspace; the roster and the history must be removed on purpose |
| A **saved lineup** | Its `lineup_player_snapshots` are deleted with it (`CASCADE`) | The snapshots belong to the lineup |
| A **player** | Nothing is deleted. Snapshots of old lineups keep the name and NSSZ number, only their `source_player_id` becomes `NULL` (`SET NULL`) | A saved lineup is a frozen copy, deleting a player does not rewrite history |
| An **invitation** | Nothing. The link stops working | Only the SHA-256 hash of the code is stored |
| A **team member** row | Nothing. The person loses access to the team | |
| A **user** in Authentication → Users | Nothing in `public`. `user_id`, `created_by` and `invited_by` are plain UUID columns, not foreign keys (`auth.users` is another schema), so the rows stay behind | See section 5 |

The `RESTRICT` error you will meet is `update or delete on table "teams" violates foreign key
constraint ... on table "players"` (or `"saved_lineups"`). It is the database protecting you:
delete the children first, in the order of section 4.

## 3. Find a user, a team or a membership

Run these in **SQL Editor** (they only read). Replace the values in quotes.

```sql
-- A user by Google e-mail (auth.users is only visible to the postgres role, i.e. here)
select id, email, created_at, last_sign_in_at
from auth.users
where email = 'someone@gmail.com';

-- Which teams is that user in, and as what?
select t.id, t.name, m.role, m.joined_at
from team_members m
join teams t on t.id = m.team_id
where m.user_id = '<user id from the first query>';

-- A team by name, with its size
select t.id, t.name, t.is_public, t.created_at,
       (select count(*) from team_members m where m.team_id = t.id) as members,
       (select count(*) from players p where p.team_id = t.id) as players,
       (select count(*) from saved_lineups l where l.team_id = t.id) as lineups
from teams t
where t.name ilike '%name%';

-- Everyone in one team (ids only: the API stores no names or e-mails, look them up in auth.users)
select m.user_id, m.role, m.joined_at, u.email
from team_members m
left join auth.users u on u.id = m.user_id
where m.team_id = '<team id>'
order by m.role, m.joined_at;

-- Active invitation links of a team (the code itself is not stored, only its hash)
select id, role, invited_by, invited_by_name, expires_at, revoked_at
from team_invitations
where team_id = '<team id>'
order by expires_at desc;
```

Authentication → Users shows the same accounts as a table with a search box, which is easier for
"who signed in last".

## 4. Delete things

Every deletion follows the same four steps:

1. **Back up** what you are about to remove (section 6, at least the rows you will delete).
2. **Select first**: run the query with `select *` and the exact `WHERE` you will use. Check the row
   count and the names.
3. **Delete with `returning *`**, so the editor prints exactly what was removed. Copy that result
   somewhere safe (a private note), it is your undo material.
4. **Check** with the select again: it must now return nothing.

The `returning *` output only exists for as long as the result tab is open. Do not close it before
you have saved it.

### Revoke an invitation (prefer this to deleting)

Revoking keeps the row, so it can be undone, and the app already treats a revoked link as "gone"
(HTTP 410). The `*_at` columns are `timestamptz`, so `now()` is right as it is:

```sql
update team_invitations
set revoked_at = now()
where id = '<invitation id>'
returning *;
```

**Undo:** `update team_invitations set revoked_at = null where id = '<invitation id>';`
(an expired link stays expired).

Delete an invitation outright only if you must remove the inviter's display name
(`invited_by_name`) before the automatic purge, which removes rows a week after `expires_at`.
`delete from team_invitations where id = '<invitation id>' returning *;` **Undo:** you cannot get
the link back, because the code was never stored. Create a new one in the app.

### Delete a player

```sql
select * from players where id = '<player id>';
delete from players where id = '<player id>' returning *;
```

**Warning:** old saved lineups still show this person's name and NSSZ number in
`lineup_player_snapshots`. For a **GDPR erasure** that is not enough, see "A person's data" below.
**Undo:** `insert` the returned row again with the same `id` (or re-create the player in the app,
which gets a new `id`; old snapshots stay detached).

### Delete a saved lineup

```sql
select id, match_name, date, team_name from saved_lineups where id = '<lineup id>';
delete from saved_lineups where id = '<lineup id>' returning *;
```

**Warning:** its player snapshots go with it (`CASCADE`), and they are not part of the
`returning *` output. Run `select * from lineup_player_snapshots where saved_lineup_id = '<lineup id>';`
first and keep that result. **Undo:** only from a backup or those saved rows.

### Delete a whole team

The order matters, because of `RESTRICT`: lineups, then players, then the team.

```sql
-- 1. Look at what you are about to destroy
select 'lineups'   as what, count(*) from saved_lineups where team_id = '<team id>'
union all select 'players',     count(*) from players       where team_id = '<team id>'
union all select 'members',     count(*) from team_members  where team_id = '<team id>'
union all select 'invitations', count(*) from team_invitations where team_id = '<team id>';

-- 2. Delete the children, then the team
delete from saved_lineups where team_id = '<team id>' returning id, match_name, date;
delete from players       where team_id = '<team id>' returning id, name;
delete from teams         where id      = '<team id>' returning *;
```

**Warning:** the third statement also deletes the team's `team_members` and `team_invitations`
silently (`CASCADE`), and sets `source_team_id` / `source_opponent_id` to `NULL` on lineups of
*other* teams that used it as an opponent. The members lose access immediately and see "no team".
**Undo:** only from a backup. There is no soft delete.

The app can do the easy cases itself: an owner can delete an empty team from the UI (409 while
it has players or lineups). Use SQL only when the app can't, for example when no owner is left.

### A person's data (erasure request)

Follow [[Privacy and Security]], section 9, which says who must ask and what to log. The database
part, for a **player**:

```sql
-- Find every trace by name and NSSZ number (the snapshots are copies, not references)
select s.id, s.saved_lineup_id, s.name, s.nssz_number
from lineup_player_snapshots s
where s.name = 'Full Name' and s.nssz_number = '123456';
```

After checking the list, delete the roster `players` row, then the matching snapshots with the
same `WHERE` and `returning *`, and write what was removed to the private request log (no names in
the public repo). A snapshot row is a slot in a lineup, so the lineup will then show one player
fewer: tell the club.

## 5. Delete a user account

1. Make sure they are not the **last owner** of a team that still has other members: transfer
   ownership in the app first (the API refuses to leave a team ownerless, SQL does not).
2. Remove them from their teams:
   ```sql
   select * from team_members where user_id = '<user id>';
   delete from team_members where user_id = '<user id>' returning *;
   ```
3. **Authentication → Users**, find the person, open the `…` menu, **Delete user**. Confirm.
   Their sign-in is gone and cannot be undone (they can sign up again, as a new user with a new id).
4. Their access token stays valid for about an hour, but with no membership it grants nothing.

What remains: the UUID in `created_by` / `invited_by` on rows they created. It is audit-only and
no longer maps to a person once the Auth user is gone. If you must remove even that, set it to the
all-zero UUID rather than deleting the rows:
`update players set created_by = '00000000-0000-0000-0000-000000000000' where created_by = '<user id>';`
(the column is `NOT NULL`; repeat for `saved_lineups`, `teams` and `team_invitations`).

## 6. Back up before a destructive change

The Free plan keeps no backups ([[Privacy and Security]], section 7; a real backup and restore plan
is #164, parked). Until then, you are the backup.

**Small change (a few rows):** the `returning *` result from section 4, or in the SQL editor the
**Download CSV** button on the result. Keep the file private; it contains personal data.

**Whole database:** with `pg_dump` (PostgreSQL client tools) and the **owner** credentials through
the **session** pooler (port 5432; the transaction pooler on 6543 does not work for `pg_dump`).
Copy the connection string from **Connect** in the dashboard, plain `postgresql://` form (no
`+asyncpg`), and keep it out of your shell history:

```bash
read -rs DUMP_URL            # paste the URL, press Enter (nothing is echoed)
pg_dump "$DUMP_URL" --schema=public --no-owner --format=custom \
  --file="lineup-$(date +%F).dump"
unset DUMP_URL
```

Store the dump somewhere private and encrypted, never in the repo, and delete it when the reason is
gone: it is a copy of personal data. **Restore** (only into an empty database):
`pg_restore --no-owner --dbname="$URL" lineup-<date>.dump`. A restore has never been tried here;
rehearse it on a throw-away project before you rely on it.

## 7. Safe read-only SQL

Anything that starts with `select` is safe: it can't change data. In the SQL editor:

- run one statement at a time (select it, then **Run** runs only the selection);
- add `limit 50` to a query on a table you have not checked the size of;
- never click the AI "fix this query" suggestions for a statement that deletes or updates;
- don't save an editor snippet containing `delete` or `update` under a friendly name: a later
  click on **Run** will execute it without the check of section 4.

Useful checks that change nothing:

```sql
-- Row counts per table
select 'teams' as t, count(*) from teams
union all select 'team_members', count(*) from team_members
union all select 'players', count(*) from players
union all select 'saved_lineups', count(*) from saved_lineups
union all select 'invitations', count(*) from team_invitations;

-- Is RLS still on everywhere? (every row must say true)
select tablename, rowsecurity from pg_tables where schemaname = 'public';

-- Which migration is the database on?
select * from alembic_version;
```

If the RLS query shows a `false`, do not "fix" it here: a migration is missing or someone broke the
rule above, so tell the owner and see `backend/alembic/versions/8b1f3c2d9a47_rls_and_least_privilege_role.py`.
