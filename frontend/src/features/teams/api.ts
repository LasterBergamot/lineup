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
 * Creates a team; the caller becomes its owner. `division` is its optional default division. `isPublic` lists just the team's name in the
 * shared opponent directory (never its roster or lineups). Throws `ApiError` on failure; a 422
 * carries per-field messages (see `fieldErrors`).
 */
export async function createTeam(
  body: { name: string; division?: string; isPublic: boolean },
  client: Pick<typeof api, "POST"> = api,
): Promise<Team> {
  return request(
    client.POST("/teams", {
      body: { name: body.name, division: body.division || undefined, is_public: body.isPublic },
    }),
  );
}

/**
 * Renames a team and/or changes whether its name is listed in the opponent directory (owners
 * only). The name and the listing choice are always sent. A blank `division` is left out, which
 * the API reads as "keep the stored one": a default division can be replaced but not cleared; the
 * home venue (`homeVenue`, #296) follows the same rule. Throws
 * `ApiError`: 403 for a member who is not the owner, 404 for someone outside the team, 422 with
 * per-field messages (see `fieldErrors`).
 */
export async function updateTeam(
  teamId: string,
  body: { name: string; division?: string; homeVenue?: string; isPublic: boolean },
  client: Pick<typeof api, "PUT"> = api,
): Promise<Team> {
  return request(
    client.PUT("/teams/{team_id}", {
      params: { path: { team_id: teamId } },
      body: {
        name: body.name,
        division: body.division || undefined,
        home_venue: body.homeVenue || undefined,
        is_public: body.isPublic,
      },
    }),
  );
}
