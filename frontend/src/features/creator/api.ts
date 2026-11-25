import { api } from "@/api/client";
import { ApiError, request } from "@/api/errors";
import type { components } from "@/api/schema";

/**
 * A saved lineup as the API returns it: a copy of the names and numbers taken when it was saved or
 * last edited. `updated_at` is the version to send back as `expected_updated_at` when editing it.
 */
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

/**
 * One saved lineup by id (`GET /lineups/saved/{id}`), used to start "Clone to new match" or
 * "Edit" from just the id. Throws `ApiError`: 404 for a lineup that is gone or belongs to a team
 * the caller is not in.
 */
export async function getSavedLineup(
  id: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<SavedLineup> {
  return request(client.GET("/lineups/saved/{lineup_id}", { params: { path: { lineup_id: id } } }));
}

/**
 * Thrown by {@link updateSavedLineup} when the lineup itself no longer exists (another member
 * deleted it), as opposed to a 404 for a roster player or an opponent picked in it. It is a 404
 * `ApiError`, so `describeError` still gives a generic text.
 */
export class SavedLineupGoneError extends ApiError {
  constructor() {
    super(404);
    this.name = "SavedLineupGoneError";
  }
}

/**
 * Edits a saved lineup in place (`PUT /lineups/saved/{id}`, #290): every field and all player
 * slots are replaced, and roster ids are resolved again, so a picked player is copied with their
 * current name and NSSZ number. `body.expected_updated_at` is the `updated_at` of the version the
 * form was loaded from. Throws `ApiError`: 409 when someone saved the lineup since (nothing was
 * changed: reload it), 422 with per-field messages, and 404 for an id the caller may not use. On a
 * 404 it asks for the lineup once more, and throws {@link SavedLineupGoneError} when the lineup
 * itself is gone, so the form can say so instead of blaming a player or the opponent.
 */
export async function updateSavedLineup(
  id: string,
  body: components["schemas"]["SavedLineupUpdate"],
  client: Pick<typeof api, "GET" | "PUT"> = api,
): Promise<SavedLineup> {
  try {
    return await request(
      client.PUT("/lineups/saved/{lineup_id}", { params: { path: { lineup_id: id } }, body }),
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404 && (await isGone(id, client))) {
      throw new SavedLineupGoneError();
    }
    throw error;
  }
}

/** Whether `GET /lineups/saved/{id}` says 404; any other failure counts as "not known to be gone". */
async function isGone(id: string, client: Pick<typeof api, "GET">): Promise<boolean> {
  try {
    await getSavedLineup(id, client);
    return false;
  } catch (error) {
    return error instanceof ApiError && error.status === 404;
  }
}
