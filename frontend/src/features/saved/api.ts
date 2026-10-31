import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/**
 * A saved lineup: a frozen copy of the match, the staff and every player's name and NSSZ number
 * as they were when it was saved. Later roster changes never reach it.
 */
export type SavedLineup = components["schemas"]["SavedLineupResponse"];

/**
 * Query key for a team's saved lineups. Every key of this feature starts with
 * `["saved", userId, teamId]`, so the lineup creator can refresh them all after saving with one
 * `invalidateQueries({ queryKey: ["saved"] })`. Ids only, never a name, and the user id keeps
 * two people on one device apart.
 */
export const savedLineupsKey = (userId: string | null, teamId: string) =>
  ["saved", userId, teamId] as const;

/**
 * Query key for the PDF preview of one saved lineup, under {@link savedLineupsKey}. A snapshot
 * never changes, so the cached file never goes stale; it lives in memory only.
 */
export const savedPreviewKey = (userId: string | null, teamId: string, lineupId: string) =>
  [...savedLineupsKey(userId, teamId), "preview", lineupId] as const;

/** The most lineups one request can return (the API caps `limit` at 200). */
const PAGE_SIZE = 200;

/**
 * Every saved lineup of `teamId`, **newest first**. The API lists the oldest first, and a team
 * saves a sheet for every match, so this reads every page (stopping at `total`, or at an empty page
 * if lineups are deleted meanwhile) and reverses the result. Throws `ApiError` on failure.
 */
export async function listSavedLineups(
  teamId: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<SavedLineup[]> {
  const lineups: SavedLineup[] = [];
  for (;;) {
    const page = await request(
      client.GET("/lineups/saved", {
        params: { query: { team_id: teamId, limit: PAGE_SIZE, offset: lineups.length } },
      }),
    );
    lineups.push(...page.items);
    if (page.items.length === 0 || lineups.length >= page.total) return lineups.reverse();
  }
}

/**
 * Deletes a saved lineup for every member of its team. Throws `ApiError`: 404 if it is already
 * gone (another member deleted it) or belongs to a team the caller is not in.
 */
export async function deleteSavedLineup(
  lineupId: string,
  client: Pick<typeof api, "DELETE"> = api,
): Promise<void> {
  await request(
    client.DELETE("/lineups/saved/{lineup_id}", { params: { path: { lineup_id: lineupId } } }),
  );
}
