import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/** A saved lineup as the API returns it: a frozen copy of the names and numbers at save time. */
export type SavedLineup = components["schemas"]["SavedLineupResponse"];

/**
 * Saves a lineup in the team's workspace (`POST /lineups/saved`). Throws `ApiError`: 404 when the
 * team, a roster player or the opponent id is not one the caller may use, 422 with per-field
 * messages (see `fieldErrors`).
 */
export async function createSavedLineup(
  body: components["schemas"]["SavedLineupCreate"],
  client: Pick<typeof api, "POST"> = api,
): Promise<SavedLineup> {
  return request(client.POST("/lineups/saved", { body }));
}
