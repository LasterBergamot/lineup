/**
 * Makes a "where to go after sign-in" value safe to navigate to. Only an absolute path on this
 * site is accepted; anything else (another origin, `//host`, a backslash trick, a `javascript:`
 * URL) falls back to the home page, so the sign-in page can never be used as an open redirect.
 */
export function safeReturnPath(raw: string | null | undefined): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || /[\\\p{Cc}]/u.test(raw)) return "/";
  // The path must resolve to this site even after the URL parser normalises it.
  try {
    const base = "http://local.invalid";
    const url = new URL(raw, base);
    if (url.origin !== base) return "/";
    return url.pathname + url.search + url.hash;
  } catch {
    return "/";
  }
}

const RETURN_KEY = "lineup-return-to";

/**
 * Remembers where the user was heading before being sent to sign in. The OAuth round trip leaves
 * the site and comes back to `/sign-in`, so this survives in `sessionStorage` (a path only,
 * never personal data) instead of in the redirect URL, which Supabase matches against an allow-list.
 */
export function rememberReturnPath(path: string): void {
  sessionStorage.setItem(RETURN_KEY, safeReturnPath(path));
}

/** The remembered path (sanitised); `/` when there is none. A pure read, safe during render. */
export function readReturnPath(): string {
  return safeReturnPath(sessionStorage.getItem(RETURN_KEY));
}

/** Forgets the remembered path (on sign-out, so it can't leak into the next person's sign-in). */
export function clearReturnPath(): void {
  sessionStorage.removeItem(RETURN_KEY);
}
