import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";

/** One player on a team's roster: a name and an NSSZ number, nothing else (data minimisation). */
export type Player = components["schemas"]["PlayerResponse"];

/** What the add/edit form sends; the team comes from the page, not from the user. */
export interface PlayerInput {
  name: string;
  nsszNumber: string;
}

/**
 * Query key for a team's roster. It holds ids only (never a name or NSSZ number) and includes the
 * user id so cached data never mixes two people on the same device.
 */
export const playersKey = (userId: string | null, teamId: string) =>
  ["players", userId, teamId] as const;

/** The most players one request can return (the API caps `limit` at 200). */
const PAGE_SIZE = 200;

/**
 * The whole roster of `teamId`, in the API's order (oldest first). Unlike `listTeams`, this reads
 * every page: a club keeping its youth squads in one team can pass 200 players, and a roster that
 * silently stops at the cap would look like lost data. The loop stops at `total`, or at an empty
 * page in case players are deleted meanwhile. Throws `ApiError` on failure.
 */
export async function listPlayers(
  teamId: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<Player[]> {
  const players: Player[] = [];
  for (;;) {
    const page = await request(
      client.GET("/players", {
        params: { query: { team_id: teamId, limit: PAGE_SIZE, offset: players.length } },
      }),
    );
    players.push(...page.items);
    if (page.items.length === 0 || players.length >= page.total) return players;
  }
}

/**
 * Adds a player to the roster of `teamId`. Throws `ApiError`: 404 if the team is gone or the
 * caller is no longer in it, 422 with per-field messages (see `fieldErrors`).
 */
export async function createPlayer(
  teamId: string,
  input: PlayerInput,
  client: Pick<typeof api, "POST"> = api,
): Promise<Player> {
  return request(
    client.POST("/players", {
      body: { team_id: teamId, name: input.name, nssz_number: input.nsszNumber },
    }),
  );
}

/**
 * Replaces a player's name and NSSZ number. `PUT` overwrites every field, `team_id` included, so
 * the current team is sent back to keep the player where it is. Saved lineups are not touched:
 * they hold their own copy. Throws `ApiError` (404 for a player that is gone, 422 per field).
 */
export async function updatePlayer(
  player: Pick<Player, "id" | "team_id">,
  input: PlayerInput,
  client: Pick<typeof api, "PUT"> = api,
): Promise<Player> {
  return request(
    client.PUT("/players/{player_id}", {
      params: { path: { player_id: player.id } },
      body: { team_id: player.team_id, name: input.name, nssz_number: input.nsszNumber },
    }),
  );
}

/**
 * Deletes a player from the roster. Saved lineups keep their frozen copy of the name and NSSZ
 * number, so this does not change any lineup already saved. Throws `ApiError` on failure.
 */
export async function deletePlayer(
  playerId: string,
  client: Pick<typeof api, "DELETE"> = api,
): Promise<void> {
  await request(
    client.DELETE("/players/{player_id}", { params: { path: { player_id: playerId } } }),
  );
}
