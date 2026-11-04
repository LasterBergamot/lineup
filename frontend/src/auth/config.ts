/** Thrown when the build has no (or an unsafe) Supabase configuration. The message is safe to show. */
export class AuthConfigError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthConfigError";
  }
}

export interface SupabaseConfig {
  /** The project URL, e.g. `https://<ref>.supabase.co`. */
  url: string;
  /** The publishable (anon) key. Public by design: it only unlocks what Auth and RLS allow. */
  publishableKey: string;
}

interface SupabaseEnv {
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
  readonly VITE_AUTH_SAME_ORIGIN?: string;
}

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

/** True when a legacy JWT-style key carries the `service_role` claim (a server-side secret). */
function isServiceRoleJwt(key: string): boolean {
  const payload = key.split(".")[1];
  if (!payload) return false;
  try {
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return (JSON.parse(json) as { role?: unknown }).role === "service_role";
  } catch {
    return false;
  }
}

/**
 * Reads and checks `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`. Everything with a `VITE_`
 * prefix is bundled into public JavaScript, so a secret key here would leak to every visitor:
 * the new `sb_secret_...` keys and legacy `service_role` JWTs are refused outright. The URL must
 * be `https` (plain `http` only for localhost, where the local stand-in for Supabase Auth runs).
 *
 * With `VITE_AUTH_SAME_ORIGIN=true` (the self-hosted web image, where a reverse proxy serves Auth
 * under the app's own origin) the auth URL is `origin` and `VITE_SUPABASE_URL` is ignored, so the
 * build holds no domain. Every other check, https included, still applies to that origin. Unset,
 * the behaviour is unchanged, which keeps the Cloudflare Pages build as it was.
 *
 * @param env The build-time settings; defaults to Vite's `import.meta.env`.
 * @param origin The page's own origin; defaults to `window.location.origin`. Used only with the flag.
 * @throws {AuthConfigError} when either value is missing, malformed or a secret key.
 */
export function readSupabaseConfig(
  env: SupabaseEnv = import.meta.env as SupabaseEnv,
  origin: string = window.location.origin,
): SupabaseConfig {
  const rawUrl = env.VITE_AUTH_SAME_ORIGIN === "true" ? origin : env.VITE_SUPABASE_URL?.trim();
  const key = env.VITE_SUPABASE_ANON_KEY?.trim();
  if (!rawUrl || !key) {
    throw new AuthConfigError(
      "Sign-in is not configured: set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY (see frontend/.env.example).",
    );
  }
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new AuthConfigError("VITE_SUPABASE_URL is not a valid URL.");
  }
  if (url.protocol !== "https:" && !(url.protocol === "http:" && LOCAL_HOSTS.has(url.hostname))) {
    throw new AuthConfigError(
      "VITE_SUPABASE_URL must use https (http is only allowed for localhost).",
    );
  }
  if (key.startsWith("sb_secret_") || isServiceRoleJwt(key)) {
    throw new AuthConfigError(
      "VITE_SUPABASE_ANON_KEY holds a secret key. Use the publishable key: this value is shipped to every browser.",
    );
  }
  return { url: url.origin, publishableKey: key };
}
