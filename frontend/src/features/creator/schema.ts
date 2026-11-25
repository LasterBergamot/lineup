import { z } from "zod";
import { errorKey } from "@/i18n/error-key";
import { cleanText, optionalCleanText } from "@/lib/clean-text";
import { matchDateSchema, matchTimeSchema } from "@/lib/match-date";
import { checkCapRows } from "@/features/lineup/cap-rows";
import { CAP_COLOURS, capNumberSchema, MAX_PLAYERS } from "@/features/lineup/schema";

/**
 * One cap row (`features/lineup/cap-rows.ts`). `playerId` is the roster player picked for it, or
 * `""` for a player typed in by hand. Either way `name` and `nssz_number` hold what the sheet will
 * print: picking a roster player copies their current values in, so the preview and the duplicate
 * checks see one shape. A row with neither is empty and is left out of the requests.
 */
const slotSchema = z.object({
  cap_number: capNumberSchema,
  playerId: z.string(),
  name: z.string(),
  nssz_number: z.string(),
});

/**
 * What the lineup creator edits. It mirrors the API's `SavedLineupCreate` limits (the backend is
 * the authority) with two differences: the team is the current team and not a field, and the
 * opponent is one text box (`opponent`) plus the directory id (`opponentId`, `""` for free text)
 * that the combobox sets when the typed name is a listed team. The match date is a
 * `YYYY-MM-DD` string and the optional start time `HH:MM` or blank, as the native inputs hold them.
 */
export const creatorSchema = z.object({
  match_name: optionalCleanText(200, "fields.match"),
  opponent: cleanText(120, "fields.opponent"),
  opponentId: z.string(),
  division: cleanText(100, "fields.division"),
  cap: z.enum(CAP_COLOURS, { error: errorKey("validation.capColour") }),
  location: optionalCleanText(200, "fields.location"),
  match_date: matchDateSchema,
  match_time: matchTimeSchema,
  coach: cleanText(200, "fields.coach"),
  doctor: optionalCleanText(200, "fields.doctor"),
  assistant_coach: optionalCleanText(200, "fields.assistantCoach"),
  team_leader: optionalCleanText(200, "fields.teamLeader"),
  ball_thrower: optionalCleanText(200, "fields.ballThrower"),
  players: z
    .array(slotSchema)
    .max(MAX_PLAYERS, errorKey("validation.maxPlayers", { max: MAX_PLAYERS }))
    .superRefine(checkCapRows),
});

export type CreatorValues = z.infer<typeof creatorSchema>;
