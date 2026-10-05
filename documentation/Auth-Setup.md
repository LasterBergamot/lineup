# Auth Setup

How sign-in works and the one-off clicks needed to switch it on for a Supabase project (dev now,
prod later). The code side is already done; this page is the manual part that lives in the Google
and Supabase dashboards. Menu names change now and then, so follow the intent if a label differs.

## How sign-in fits together

```mermaid
sequenceDiagram
    participant U as User (browser)
    participant FE as Frontend
    participant S as Supabase Auth
    participant G as Google
    participant API as Lineup API

    U->>FE: Sign in with Google
    FE->>S: supabase-js starts the OAuth flow
    S->>G: redirect (our OAuth client)
    G-->>S: who the user is (if on the test-user list)
    S-->>FE: session with an access token (JWT)
    FE->>API: request + Authorization: Bearer <JWT>
    API->>S: (rarely) download the public signing keys
    API-->>FE: data for that user only
```

- The browser talks to Supabase **only to sign in**. All data goes through our API.
- The API never holds a secret for this. It downloads Supabase's *public* signing keys and
  checks each token with them (`backend/lineup/auth/tokens.py`).
- The Google **client secret** lives only in the Supabase dashboard. It must never be committed,
  put in `backend/.env` or sent to the frontend.

## 1. Google Cloud console (once per environment)

1. Create (or pick) a Google Cloud project and open **Google Auth Platform**.
2. **Branding / Audience**: set the app name and support email. Keep the **Publishing status** at
   **Testing** for dev. In Testing mode only the addresses on the *Test users* list can sign in;
   anyone else is stopped by Google itself ("Access blocked ... error 403: access_denied") and never
   reaches Supabase.
3. **Clients** → create an **OAuth client ID**, application type **Web application**. Under
   *Authorized redirect URIs* add exactly
   `https://<project-ref>.supabase.co/auth/v1/callback`
   (`<project-ref>` is the id in the Supabase project URL).
4. Copy the client ID and client secret for the next step.

## 2. Supabase dashboard (dev project)

1. **Authentication → Sign In / Providers → Google**: enable it and paste the client ID and secret.
2. **Authentication → URL Configuration**:
   - *Site URL*: the dev frontend URL (until it exists, `http://localhost:5173`).
   - *Redirect URLs*: `http://localhost:5173/**`, the dev Cloudflare Pages URL and
     `https://*.<pages-project>.pages.dev/**` (PR previews) once they exist.
3. **Project Settings → JWT Keys (JWT Signing Keys)**: the API only accepts tokens signed with an
   **asymmetric** key (ECC P-256 / `ES256` or RSA / `RS256`). Projects created before Supabase's
   signing-keys feature use the legacy shared secret (`HS256`), which the API deliberately
   rejects: a shared secret can't be verified without being able to forge tokens. If the page
   offers "Migrate JWT secret", do it, and make an asymmetric key the one that signs. Check that
   `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` lists at least one key.
4. Leave the **Data API** off. Supabase Auth is a separate service and keeps working.

## 3. Point the API at the project

Set one variable (`backend/.env` locally, `fly secrets set` on Fly later):

```
SUPABASE_URL="https://<project-ref>.supabase.co"
```

From it the API derives the token issuer (`<SUPABASE_URL>/auth/v1`) and the key-set address
(`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`). It must be `https`; plain `http` is accepted
only for `localhost` (the Supabase CLI). Audience is always `authenticated`.

If it is unset or invalid, every protected route answers `503 Authentication unavailable`
(fail closed) and the server log says why.

### Frontend settings

The frontend needs two public values in `frontend/.env` (copy `frontend/.env.example`; on Cloudflare
Pages later they are build-time environment variables):

```
VITE_SUPABASE_URL="https://<project-ref>.supabase.co"
VITE_SUPABASE_ANON_KEY="<the publishable key>"
```

Both are on **Project Settings → API**. Use the **publishable** key (`sb_publishable_...`, or the
legacy `anon` key). Everything with a `VITE_` prefix is shipped to every visitor, so the app
**refuses to start sign-in** if the value is a secret key (`sb_secret_...` or a `service_role` JWT)
and says why on the sign-in page. The redirect allow-list from section 2 must contain the address the
app runs on, because Google sends the browser back to `<app>/sign-in`.

## 4. Who may sign in

| Task | Where | Effect |
|---|---|---|
| Add a tester | Google Cloud console → Google Auth Platform → Audience → **Test users** → add their Google address (up to 100) | Takes effect immediately. They see a one-time "Google hasn't verified this app" screen and click Continue. |
| Remove a tester | Remove the address from the same list **and** delete them under Supabase → Authentication → **Users** | The list stops *new* sign-ins; an existing session stays valid until its token expires (about an hour), so delete the user to cut them off. |

Supabase has no e-mail allowlist for OAuth; the Google list is the gate while the consent screen is in Testing mode. For prod, decide later between publishing the consent screen and an allowlist in the API.

## 5. Check that it works

1. Sign in through the frontend (or any supabase-js snippet) and copy the session's
   `access_token`.
2. `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/teams` should return `200`;
   without the header it returns `401`.

## Trying the frontend without Google (local only)

`scripts/smoke_auth.py` is a stand-in for Supabase Auth: it serves a throw-away public key set and
writes a token for a random user to a file. It does **not** implement the Google redirect, so the
*Continue with Google* button cannot finish against it, but everything after sign-in can be
exercised:

1. `uv run --project backend python scripts/smoke_auth.py --port 54399 --token-file /tmp/dev.jwt`
2. In `backend/`: `SUPABASE_URL=http://127.0.0.1:54399 CORS_ORIGINS=http://localhost:5173 uv run uvicorn app:app --port 8001`
3. In `frontend/`: `VITE_API_URL=http://127.0.0.1:8001 VITE_SUPABASE_URL=http://127.0.0.1:54399 VITE_SUPABASE_ANON_KEY=sb_publishable_local pnpm dev`
4. In the browser console on `http://localhost:5173`, store a session for the token (the storage key
   is `sb-` plus the first part of the Supabase host, here `sb-127-auth-token`), then reload:
   `localStorage.setItem("sb-127-auth-token", JSON.stringify({access_token: "<token>", refresh_token: "x", token_type: "bearer", expires_in: 3000, expires_at: Math.floor(Date.now()/1000)+3000, user: {id: "<the token's sub>", aud: "authenticated"}}))`

You then land in onboarding (no team yet), can create a team and see the shell. Delete the token
file afterwards; it is a valid credential for that throw-away key set only.

## Troubleshooting

The API answers `401 {"detail":"Not authenticated"}` for every rejected token on purpose (the
client learns nothing about why). The reason is in the server log as `Authentication rejected:
<code>` (never the token itself):

| Code | Meaning |
|---|---|
| `missing_token` | No `Authorization: Bearer ...` header |
| `malformed` | Not a JWT |
| `disallowed_alg` | Header `alg` is not `ES256`/`RS256` (e.g. a legacy `HS256` project, or `none`) |
| `missing_kid` / `unknown_kid` | No key id, or Supabase has no such key (rotated, or a different project) |
| `bad_signature` | Signature doesn't match the key |
| `expired` / `not_yet_valid` | `exp` / `nbf` outside the 10 s clock skew |
| `wrong_audience` / `wrong_issuer` | Not an end-user token, or from another project (check `SUPABASE_URL`) |
| `invalid` / `bad_subject` | A required claim is missing, or `sub` is not a UUID |

`503 Authentication unavailable` means the API cannot check tokens at all: `SUPABASE_URL` is unset
or malformed, or the key set could not be downloaded (Supabase paused on the free tier, or
unreachable).
