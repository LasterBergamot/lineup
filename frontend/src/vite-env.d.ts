/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Lineup API; empty means the same-origin `/api` dev proxy. */
  readonly VITE_API_URL?: string;
  /** The Supabase project URL, used for Google sign-in only (all data goes through the API). */
  readonly VITE_SUPABASE_URL?: string;
  /** The Supabase *publishable* key. Public by design; a secret/service-role key is refused at startup. */
  readonly VITE_SUPABASE_ANON_KEY?: string;
  /** `"false"` hides the "server is waking up" banner. */
  readonly VITE_COLD_START_NOTICE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
