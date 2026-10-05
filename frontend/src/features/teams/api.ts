import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/** A team the signed-in user belongs to; `role` is theirs in it (`owner` or `member`). */
export type Team = components["schemas"]["TeamResponse"];

/** Query key for a user's teams; it includes the user id so cached data never mixes two people. */
export const teamsKey = (userId: string | null) => ["teams", userId] as const;

/** The most teams one request can return (the API caps `limit` at 200). */
const PAGE_SIZE = 200;

/**
 * Every team the caller belongs to, ordered by name. One page is enough: a person belongs to a
 * handful of clubs, far below the cap. Throws `ApiError` on failure.
 */
export async function listTeams(client: Pick<typeof api, "GET"> = api): Promise<Team[]> {
  const page = await request(client.GET("/teams", { params: { query: { limit: PAGE_SIZE } } }));
  return page.items;
}

/**
 * Creates a team; the caller becomes its owner. `isPublic` lists just the team's name in the
 * shared opponent directory (never its roster or lineups). Throws `ApiError` on failure; a 422
 * carries per-field messages (see `fieldErrors`).
 */
export async function createTeam(
  body: { name: string; isPublic: boolean },
  client: Pick<typeof api, "POST"> = api,
): Promise<Team> {
  return request(client.POST("/teams", { body: { name: body.name, is_public: body.isPublic } }));
}
