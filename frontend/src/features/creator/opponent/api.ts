import { api } from "@/api/client";
import { request } from "@/api/errors";

/**
 * Query key for a team's recent opponents. It holds ids only and includes the user id so cached
 * data never mixes two people on the same device. Saving a lineup should invalidate it.
 */
export const recentOpponentsKey = (userId: string | null, teamId: string) =>
  ["recent-opponents", userId, teamId] as const;

/**
 * The opponent names used in `teamId`'s own saved lineups, most recent first and without
 * duplicates (`limit` 1-50). They cover clubs that never signed up, without adding them to the
 * shared directory. Throws `ApiError`: 404 when the caller is not a member of the team.
 */
export async function listRecentOpponents(
  teamId: string,
  limit = 20,
  client: Pick<typeof api, "GET"> = api,
): Promise<string[]> {
  return request(
    client.GET("/teams/{team_id}/opponents/recent", {
      params: { path: { team_id: teamId }, query: { limit } },
    }),
  );
}
