import createClient from "openapi-fetch";
import type { paths } from "./schema";

/**
 * Where the API lives. Deployed builds set `VITE_API_URL`; in local dev it is empty and the
 * Vite dev server proxies the same-origin `/api` prefix to the container (no CORS needed).
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

/** Builds a typed fetch client; request and response types come from the backend's OpenAPI spec. */
export function createApi(baseUrl: string = API_BASE_URL) {
  return createClient<paths>({ baseUrl });
}

/** The app-wide client. */
export const api = createApi();
