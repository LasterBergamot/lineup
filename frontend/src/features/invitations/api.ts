import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";
import type { Team } from "@/features/teams/api";

/** What anyone holding a link may see before signing in: team name, inviter's name, expiry. */
export type InvitationPreview = components["schemas"]["InvitationPreview"];
/** A freshly made link. `code` and `url` exist only in this response, never again. */
export type InvitationCreated = components["schemas"]["InvitationCreated"];
/** An active link as the owner's list shows it (no code: only a hash is stored). */
export type Invitation = components["schemas"]["InvitationResponse"];

/** The lifetimes the API accepts for a new link, in hours. */
export const EXPIRY_CHOICES = [2, 24, 72] as const;
export type ExpiryHours = (typeof EXPIRY_CHOICES)[number];
/** What the API uses when no lifetime is sent; short, so a forwarded link does little harm. */
export const DEFAULT_EXPIRY: ExpiryHours = 24;

/** Query key for a team's active links; it includes the user id so cached data never mixes people. */
export const invitationsKey = (userId: string | null, teamId: string) =>
  ["invitations", userId, teamId] as const;

/** Query key for a link's public preview. The code lives only in memory, never in storage. */
export const invitationPreviewKey = (code: string) => ["invitation-preview", code] as const;

/**
 * What a link is for (public, needs no sign-in). Throws `ApiError`: 404 for an unknown code,
 * 410 for an expired or revoked one.
 */
export async function previewInvitation(
  code: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<InvitationPreview> {
  return request(client.GET("/invitations/{code}", { params: { path: { code } } }));
}

/**
 * Joins the team behind a link as a member (idempotent: an existing member stays what they are).
 * Returns the team with the caller's role. Throws `ApiError` (404 unknown, 410 expired or revoked).
 */
export async function acceptInvitation(
  code: string,
  client: Pick<typeof api, "POST"> = api,
): Promise<Team> {
  return request(client.POST("/invitations/{code}/accept", { params: { path: { code } } }));
}

/** Makes a link for the team (owners only). Throws `ApiError`: 403 for a member, 404 for a non-member. */
export async function createInvitation(
  teamId: string,
  expiresInHours: ExpiryHours,
  client: Pick<typeof api, "POST"> = api,
): Promise<InvitationCreated> {
  return request(
    client.POST("/teams/{team_id}/invitations", {
      params: { path: { team_id: teamId } },
      body: { expires_in_hours: expiresInHours },
    }),
  );
}

/** The team's links that still work, newest first (owners only). */
export async function listInvitations(
  teamId: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<Invitation[]> {
  return request(
    client.GET("/teams/{team_id}/invitations", { params: { path: { team_id: teamId } } }),
  );
}

/** Stops a link working (owners only). People who already joined stay in the team. */
export async function revokeInvitation(
  teamId: string,
  invitationId: string,
  client: Pick<typeof api, "DELETE"> = api,
): Promise<void> {
  await request(
    client.DELETE("/teams/{team_id}/invitations/{invitation_id}", {
      params: { path: { team_id: teamId, invitation_id: invitationId } },
    }),
  );
}
