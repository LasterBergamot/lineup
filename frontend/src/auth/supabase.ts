import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { AuthConfigError, readSupabaseConfig } from "@/auth/config";

let client: SupabaseClient | undefined;

/**
 * The one Supabase client, created on first use. It is used for sign-in only (D6): every piece
 * of data goes through our own API, so no table is ever queried from the browser.
 *
 * PKCE keeps the OAuth result out of the URL fragment (the redirect carries a short-lived
 * one-time code that is exchanged for the session instead of the tokens themselves). The
 * session is kept in localStorage, which is strictly necessary for staying signed in.
 *
 * @throws {AuthConfigError} when the build has no usable Supabase configuration.
 */
export function getSupabase(): SupabaseClient {
  if (!client) {
    const { url, publishableKey } = readSupabaseConfig();
    client = createClient(url, publishableKey, {
      auth: {
        flowType: "pkce",
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }
  return client;
}

/**
 * The current access token, or `null` when nobody is signed in or sign-in is not configured
 * (then calls simply go out without a token). supabase-js refreshes an expired token here.
 */
export async function getAccessToken(): Promise<string | null> {
  let supabase: SupabaseClient;
  try {
    supabase = getSupabase();
  } catch (error) {
    if (error instanceof AuthConfigError) return null;
    throw error;
  }
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
