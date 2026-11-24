import { api } from "@/api/client";
import { request } from "@/api/errors";
import type { components } from "@/api/schema";
import type { ComboboxOption } from "@/components/ui/combobox";

/**
 * One staff entry of a team (#292): a role and a name, nothing else (data minimisation, G4). The
 * name is a copy: an entry picked from the roster keeps `source_player_id`, but its name does not
 * follow later renames of the player.
 */
export type Staff = components["schemas"]["StaffResponse"];

/** The roles a team keeps staff for. The doctor is not one: it stays a per-lineup free text. */
export type StaffRole = components["schemas"]["StaffRole"];

/** The roles in the order the Staff card and the lineup forms show them. */
export const STAFF_ROLES = ["coach", "assistant_coach", "team_leader", "ball_thrower"] as const;

/** The `fields.*` locale key of each role's label, shared with the lineup forms. */
export const ROLE_LABELS = {
  coach: "fields.coach",
  assistant_coach: "fields.assistantCoach",
  team_leader: "fields.teamLeader",
  ball_thrower: "fields.ballThrower",
} as const satisfies Record<StaffRole, string>;

/** What the add/edit form sends. `playerId` is the roster player it was picked from, or `""`. */
export interface StaffInput {
  role: StaffRole;
  name: string;
  playerId: string;
  isDefault: boolean;
}

/**
 * Query key for a team's staff. Ids only (never a name), with the user id so cached data never
 * mixes two people on the same device. The Roster page and the lineup page share it, so a change
 * on the Staff card reaches the lineup forms' suggestions.
 */
export const staffKey = (userId: string | null, teamId: string) =>
  ["staff", userId, teamId] as const;

/** The team's staff entries, all roles, in the API's order (oldest first). Throws `ApiError`. */
export async function listStaff(
  teamId: string,
  client: Pick<typeof api, "GET"> = api,
): Promise<Staff[]> {
  return request(client.GET("/teams/{team_id}/staff", { params: { path: { team_id: teamId } } }));
}

/** The API body for an input: a typed-in name goes without `source_player_id`. */
function body(input: StaffInput): components["schemas"]["StaffWrite"] {
  return {
    role: input.role,
    name: input.name,
    is_default: input.isDefault,
    source_player_id: input.playerId || null,
  };
}

/**
 * Adds a staff entry to `teamId`. A new default replaces the role's old one on the server. Throws
 * `ApiError`: 404 if the team (or the picked player) is gone or not reachable, 422 per field.
 */
export async function createStaff(
  teamId: string,
  input: StaffInput,
  client: Pick<typeof api, "POST"> = api,
): Promise<Staff> {
  return request(
    client.POST("/teams/{team_id}/staff", {
      params: { path: { team_id: teamId } },
      body: body(input),
    }),
  );
}

/**
 * Replaces a staff entry. `PUT` overwrites every field (role, name, source player and the default
 * flag), so the whole input is sent each time. Throws `ApiError` (404 for an entry or player that
 * is gone, 422 per field, 409 if another member made a different default at the same moment).
 */
export async function updateStaff(
  entry: Pick<Staff, "id" | "team_id">,
  input: StaffInput,
  client: Pick<typeof api, "PUT"> = api,
): Promise<Staff> {
  return request(
    client.PUT("/teams/{team_id}/staff/{staff_id}", {
      params: { path: { team_id: entry.team_id, staff_id: entry.id } },
      body: body(input),
    }),
  );
}

/**
 * Deletes a staff entry. Deleting a role's default leaves that role without one (nobody is
 * promoted), and saved lineups keep the names they printed. Throws `ApiError` on failure.
 */
export async function deleteStaff(
  entry: Pick<Staff, "id" | "team_id">,
  client: Pick<typeof api, "DELETE"> = api,
): Promise<void> {
  await request(
    client.DELETE("/teams/{team_id}/staff/{staff_id}", {
      params: { path: { team_id: entry.team_id, staff_id: entry.id } },
    }),
  );
}

const collator = new Intl.Collator("hu", { sensitivity: "base" });

/** The entries of one role: the default first, then alphabetically in Hungarian order. */
export function staffOfRole(staff: readonly Staff[], role: StaffRole): Staff[] {
  return staff
    .filter((entry) => entry.role === role)
    .sort(
      (a, b) => Number(b.is_default) - Number(a.is_default) || collator.compare(a.name, b.name),
    );
}

/**
 * The suggestions of a lineup form's staff field: that role's names in {@link staffOfRole} order,
 * each name once (two entries may share a name; the field holds text, not an entry).
 */
export function staffSuggestions(staff: readonly Staff[], role: StaffRole): ComboboxOption[] {
  const names = new Set(staffOfRole(staff, role).map((entry) => entry.name));
  return [...names].map((name) => ({ value: name, label: name }));
}

/** Each role's default name, or `""` for a role without one: what a new lineup starts with. */
export function staffDefaults(staff: readonly Staff[]): Record<StaffRole, string> {
  const name = (role: StaffRole) =>
    staff.find((entry) => entry.role === role && entry.is_default)?.name ?? "";
  return {
    coach: name("coach"),
    assistant_coach: name("assistant_coach"),
    team_leader: name("team_leader"),
    ball_thrower: name("ball_thrower"),
  };
}
