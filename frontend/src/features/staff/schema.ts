import { z } from "zod";
import { cleanText } from "@/lib/clean-text";
import { STAFF_ROLES } from "@/features/staff/api";

/**
 * The add/edit staff form. The role comes from a select of the four roles, the name mirrors the
 * API's `CleanStr200`, and `playerId` is the roster player picked (or `""` for a typed-in name);
 * the server checks that the player is on this team.
 */
export const staffFormSchema = z.object({
  role: z.enum(STAFF_ROLES),
  playerId: z.string(),
  name: cleanText(200, "fields.name"),
  isDefault: z.boolean(),
});

export type StaffFormValues = z.infer<typeof staffFormSchema>;

/** The add form's starting values: a coach, typed in, not the default. */
export const EMPTY_STAFF: StaffFormValues = {
  role: "coach",
  playerId: "",
  name: "",
  isDefault: false,
};
