import { z } from "zod";
import { errorKey } from "@/i18n/error-key";
import { cleanText, optionalCleanText } from "@/lib/clean-text";
import { CAP_COLOURS, capNumberSchema, MAX_PLAYERS } from "@/features/lineup/schema";

const NAME = cleanText(200, "fields.name");
const NSSZ = cleanText(50, "fields.nsszNumber");

/**
 * One player slot. `playerId` is the roster player picked for it, or `""` for a player typed in by
 * hand. Either way `name` and `nssz_number` hold what the sheet will print: picking a roster
 * player copies their current values in, so the preview and the duplicate checks see one shape.
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
 * that the combobox sets when the typed name is a listed team.
 */
export const creatorSchema = z.object({
  match_name: optionalCleanText(200, "fields.match"),
  opponent: cleanText(120, "fields.opponent"),
  opponentId: z.string(),
  division: cleanText(100, "fields.division"),
  cap: z.enum(CAP_COLOURS, { error: errorKey("validation.capColour") }),
  date: cleanText(50, "fields.date"),
  coach: cleanText(200, "fields.coach"),
  doctor: optionalCleanText(200, "fields.doctor"),
  assistant_coach: optionalCleanText(200, "fields.assistantCoach"),
  team_leader: optionalCleanText(200, "fields.teamLeader"),
  ball_thrower: optionalCleanText(200, "fields.ballThrower"),
  players: z
    .array(slotSchema)
    .min(1, errorKey("validation.minPlayers"))
    .max(MAX_PLAYERS, errorKey("validation.maxPlayers", { max: MAX_PLAYERS }))
    .superRefine((players, ctx) => {
      const seenCaps = new Set<number>();
      const seenNssz = new Set<string>();
      players.forEach((player, index) => {
        // A roster player is already valid; only typed-in values need the text rules.
        if (!player.playerId) {
          for (const [field, rule] of [
            ["name", NAME],
            ["nssz_number", NSSZ],
          ] as const) {
            const result = rule.safeParse(player[field]);
            if (!result.success) {
              ctx.addIssue({
                code: "custom",
                path: [index, field],
                message: result.error.issues[0]!.message,
              });
            }
          }
        }
        if (seenCaps.has(player.cap_number)) {
          ctx.addIssue({
            code: "custom",
            path: [index, "cap_number"],
            message: errorKey("validation.uniqueCapNumber"),
          });
        }
        seenCaps.add(player.cap_number);
        const nssz = player.nssz_number.trim().toLowerCase();
        if (nssz && seenNssz.has(nssz)) {
          ctx.addIssue({
            code: "custom",
            path: [index, "nssz_number"],
            message: errorKey("validation.uniqueNssz"),
          });
        }
        seenNssz.add(nssz);
      });
    }),
});

export type CreatorValues = z.infer<typeof creatorSchema>;
