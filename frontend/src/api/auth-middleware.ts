import type { Middleware } from "openapi-fetch";

/** Endpoints that never need (or should wait for) a token; `/health` is the wake-up probe. */
const PUBLIC_PATHS = new Set(["/health"]);

/**
 * Adds `Authorization: Bearer <token>` to every API call when someone is signed in, and reports
 * a `401` on a call that carried a token (so the session can be ended).
 *
 * The token never leaves this function except in that header: it is not logged, not stored and
 * not put in an error. `/health` is skipped so the wake-up probe starts immediately and, when
 * the API is on another origin, does not trigger a CORS preflight for a header it does not need.
 */
export function createAuthMiddleware(
  getToken: () => Promise<string | null>,
  onUnauthorized: () => void,
): Middleware {
  return {
    async onRequest({ request, schemaPath }) {
      if (PUBLIC_PATHS.has(schemaPath)) return;
      const token = await getToken();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
    onResponse({ request, response }) {
      if (response.status === 401 && request.headers.has("Authorization")) onUnauthorized();
    },
  };
}
