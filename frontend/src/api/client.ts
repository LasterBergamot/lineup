import createClient from "openapi-fetch";
import type { paths } from "./schema";

/**
 * Where the API lives. Deployed builds set `VITE_API_URL`; in local dev it is empty and the
 * Vite dev server proxies the same-origin `/api` prefix to the container (no CORS needed).
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

/** Ordinary calls. Generous, because a cold-starting backend holds the request while it boots. */
export const DEFAULT_TIMEOUT_MS = 60_000;

/** PDF generation; must stay at least the backend's LibreOffice timeout (`CONVERSION_TIMEOUT_SECONDS`, 120 s). */
export const PDF_TIMEOUT_MS = 130_000;

/** `fetch` that gives up after `timeoutMs` (on top of any signal the caller already set). */
export function fetchWithTimeout(timeoutMs: number): (request: Request) => Promise<Response> {
  return (request) =>
    fetch(
      new Request(request, {
        signal: AbortSignal.any([request.signal, AbortSignal.timeout(timeoutMs)]),
      }),
    );
}

/** Builds a typed fetch client; request and response types come from the backend's OpenAPI spec. */
export function createApi(baseUrl: string = API_BASE_URL, timeoutMs: number = DEFAULT_TIMEOUT_MS) {
  return createClient<paths>({ baseUrl, fetch: fetchWithTimeout(timeoutMs) });
}

/** The app-wide client. */
export const api = createApi();

/** A client with the long PDF timeout, for the endpoints that run LibreOffice. */
export const generateApi = createApi(API_BASE_URL, PDF_TIMEOUT_MS);
