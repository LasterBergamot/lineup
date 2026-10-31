import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/**
 * A team in the shared opponent directory: only teams that chose to be listed (`is_public`), and
 * only their id and name, never a roster. The caller's own team may be among them.
 */
export type PoolTeam = components["schemas"]["TeamPoolItem"];

/** Query key for one directory search; it includes the user id so cached data never mixes people. */
export const poolKey = (userId: string | null, search: string) => ["pool", userId, search] as const;

/**
 * Up to `limit` (1-100) listed teams whose name contains `search` (a literal, case-insensitive
 * substring of at most 120 characters), ordered by name. A blank `search` leaves the parameter
 * out, which returns the first teams alphabetically. Throws `ApiError` on failure.
 */
export async function searchPool(
  search: string,
  limit: number,
  client: Pick<typeof api, "GET"> = api,
): Promise<PoolTeam[]> {
  const term = search.trim();
  return request(
    client.GET("/teams/pool", {
      params: { query: term ? { search: term, limit } : { limit } },
    }),
  );
}
