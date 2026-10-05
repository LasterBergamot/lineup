/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the Lineup API; empty means the same-origin `/api` dev proxy. */
  readonly VITE_API_URL?: string;
  /** `"false"` hides the "server is waking up" banner. */
  readonly VITE_COLD_START_NOTICE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
