import { z } from "zod";
import { errorKey } from "@/i18n/error-key";
import { capRows, checkCapRows, MAX_PLAYERS, requestPlayers } from "@/features/lineup/cap-rows";
import type { components } from "@/api/schema";
import type { StaffRole } from "@/features/staff/api";
import { cleanText as text } from "@/lib/clean-text";
import { composeMatchDate, matchDateSchema, matchTimeSchema, todayIso } from "@/lib/match-date";

export const CAP_COLOURS = ["Fehér", "Kék"] as const;

export { MAX_PLAYERS };

const CAP_NUMBER_ERROR = errorKey("validation.capNumber");

/** A cap number: a whole number from 1 to 15. Shared by the one-off form and the creator. */
export const capNumberSchema = z
  .number({ error: CAP_NUMBER_ERROR })
  .int(CAP_NUMBER_ERROR)
  .min(1, CAP_NUMBER_ERROR)
  .max(MAX_PLAYERS, CAP_NUMBER_ERROR);

/** One cap row; its text is checked by `checkCapRows`, because an empty row is allowed. */
const playerSchema = z.object({
  cap_number: capNumberSchema,
  name: z.string(),
  nssz_number: z.string(),
});

/**
 * The one-off lineup form: the API's `LineupRequest` fields, with `players` as the 15 fixed cap
 * rows (`cap-rows.ts`). {@link toQuickSheetRequest} drops the empty rows before sending.
 */
export const lineupSchema = z.object({
  match: text(200, "fields.match"),
  division: text(100, "fields.division"),
  team_name: text(120, "fields.teamName"),
  cap: z.enum(CAP_COLOURS, { error: errorKey("validation.capColour") }),
  match_date: matchDateSchema,
  match_time: matchTimeSchema,
  coach: text(200, "fields.coach"),
  doctor: text(200, "fields.doctor"),
  assistant_coach: text(200, "fields.assistantCoach"),
  team_leader: text(200, "fields.teamLeader"),
  ball_thrower: text(200, "fields.ballThrower"),
  players: z
    .array(playerSchema)
    .max(MAX_PLAYERS, errorKey("validation.maxPlayers", { max: MAX_PLAYERS }))
    .superRefine(checkCapRows),
});

export type LineupFormValues = z.infer<typeof lineupSchema>;

/**
 * What the Quick sheet opens with: the 15 empty cap rows, today's date (read now, no time) and
 * each staff role's default name from `staff` (#289; empty for a role without one).
 */
export function emptyQuickSheetValues(
  staff: Partial<Record<StaffRole, string>> = {},
): Partial<LineupFormValues> {
  return {
    coach: staff.coach ?? "",
    assistant_coach: staff.assistant_coach ?? "",
    team_leader: staff.team_leader ?? "",
    ball_thrower: staff.ball_thrower ?? "",
    cap: "Fehér",
    match_date: todayIso(),
    match_time: "",
    players: capRows((cap_number) => ({ cap_number, name: "", nssz_number: "" })),
  };
}

/**
 * The body for `POST /lineups`: the form values with only the filled cap rows. The stateless
 * endpoint takes only the printed `date`, so it is composed here from the date and time inputs.
 */
export function toQuickSheetRequest(
  values: LineupFormValues,
): components["schemas"]["LineupRequest"] {
  const { match_date, match_time, ...rest } = values;
  return {
    ...rest,
    date: composeMatchDate(match_date, match_time),
    players: requestPlayers(values.players),
  };
}
