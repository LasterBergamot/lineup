import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";
import type { Team } from "@/features/teams/api";

/** One team member: ids and roles only, the API stores no names or e-mail addresses. */
export type Member = components["schemas"]["MemberResponse"];

/** Query key for a team's members; it includes the user id so cached data never mixes people. */
export const membersKey = (userId: string | null, teamId: string) =>
  ["members", userId, teamId] as const;

/** Everyone in the team, in the API's order. Throws `ApiError` (404 for a non-member). */
export async function listMembers(
  teamId: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<Member[]> {
  return request(client.GET("/teams/{team_id}/members", { params: { path: { team_id: teamId } } }));
}

/**
 * Removes a member (owners), or leaves the team when `memberId` is the caller's own id. Throws
 * `ApiError`: 403 for a member removing someone else, 409 when it would leave no owner.
 */
export async function removeMember(
  teamId: string,
  memberId: string,
  client: Pick<typeof api, "DELETE"> = api,
): Promise<void> {
  await request(
    client.DELETE("/teams/{team_id}/members/{member_id}", {
      params: { path: { team_id: teamId, member_id: memberId } },
    }),
  );
}

/** Hands the team over to another member (owners); the caller becomes a member. */
export async function transferOwnership(
  teamId: string,
  memberId: string,
  client: Pick<typeof api, "POST"> = api,
): Promise<Team> {
  return request(
    client.POST("/teams/{team_id}/transfer-ownership", {
      params: { path: { team_id: teamId } },
      body: { user_id: memberId },
    }),
  );
}
