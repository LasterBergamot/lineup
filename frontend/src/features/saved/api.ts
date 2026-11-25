import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/**
 * A saved lineup: a copy of the match, the staff and every player's name and NSSZ number as they
 * were when it was saved or last edited (#290). Later roster changes never reach it by themselves;
 * only editing the lineup copies a re-picked player's current values in.
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
 * Query key for the PDF preview of one version of a saved lineup, under {@link savedLineupsKey}.
 * `updatedAt` is the lineup's `updated_at`: an edit (#290) makes a new version and so a new key,
 * which means a cached file never shows an old version, and one version's file never goes stale.
 * It lives in memory only.
 */
export const savedPreviewKey = (
  userId: string | null,
  teamId: string,
  lineupId: string,
  updatedAt: string,
) => [...savedLineupsKey(userId, teamId), "preview", lineupId, updatedAt] as const;

/** How many lineups one request (and one "Show more" step) returns. The API allows up to 200. */
export const PAGE_SIZE = 20;

/** The API's limits on the two text filters. */
export const MAX_OPPONENT_LENGTH = 120;
export const MAX_LOCATION_LENGTH = 200;

/**
 * What the Saved page's filter bar holds. Text is a case-insensitive "contains", the dates are
 * `YYYY-MM-DD` (what `<input type="date">` gives) and inclusive; an empty string means "no
 * filter". Filters are combined, and they live in component state only, never in a URL or storage.
 */
export interface SavedFilters {
  opponent: string;
  dateFrom: string;
  dateTo: string;
  location: string;
}

/** No filter set: the full list. */
export const NO_FILTERS: SavedFilters = { opponent: "", dateFrom: "", dateTo: "", location: "" };

/** True when at least one filter has something in it (blank text does not count). */
export const hasFilters = (filters: SavedFilters) =>
  Object.values(filters).some((value) => value.trim() !== "");

/**
 * Query key for one filtered list of a team's saved lineups, under {@link savedLineupsKey}. The
 * filters are part of the key, so each combination is cached on its own and in memory only.
 */
export const savedListKey = (userId: string | null, teamId: string, filters: SavedFilters) =>
  [...savedLineupsKey(userId, teamId), "list", filters] as const;

/** One page of {@link listSavedLineups}: `total` counts every match, not just this page. */
export interface SavedPage {
  items: SavedLineup[];
  total: number;
  offset: number;
}

/**
 * One page (`PAGE_SIZE` lineups from `offset`) of `teamId`'s saved lineups matching `filters`,
 * **newest match first** as the API orders them. Blank filters are left out of the request, so no
 * filter is the plain list. Throws `ApiError` on failure.
 */
export async function listSavedLineups(
  teamId: string,
  filters: SavedFilters,
  offset = 0,
  client: Pick<typeof api, "GET"> = api,
): Promise<SavedPage> {
  const opponent = filters.opponent.trim();
  const location = filters.location.trim();
  const page = await request(
    client.GET("/lineups/saved", {
      params: {
        query: {
          team_id: teamId,
          limit: PAGE_SIZE,
          offset,
          ...(opponent && { opponent }),
          ...(filters.dateFrom && { date_from: filters.dateFrom }),
          ...(filters.dateTo && { date_to: filters.dateTo }),
          ...(location && { location }),
        },
      },
    }),
  );
  return { items: page.items, total: page.total, offset };
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
