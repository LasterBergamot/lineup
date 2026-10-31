import { z } from "zod";
import { errorKey } from "@/i18n/error-key";
import { cleanText as text } from "@/lib/clean-text";

export const CAP_COLOURS = ["Fehér", "Kék"] as const;

export const MAX_PLAYERS = 15;

const CAP_NUMBER_ERROR = errorKey("validation.capNumber");

/** A cap number: a whole number from 1 to 15. Shared by the one-off form and the creator. */
export const capNumberSchema = z
  .number({ error: CAP_NUMBER_ERROR })
  .int(CAP_NUMBER_ERROR)
  .min(1, CAP_NUMBER_ERROR)
  .max(MAX_PLAYERS, CAP_NUMBER_ERROR);

const playerSchema = z.object({
  cap_number: capNumberSchema,
  name: text(200, "fields.name"),
  nssz_number: text(50, "fields.nsszNumber"),
});

/** The one-off lineup form; the shape is exactly the API's `LineupRequest`. */
export const lineupSchema = z.object({
  match: text(200, "fields.match"),
  division: text(100, "fields.division"),
  team_name: text(120, "fields.teamName"),
  cap: z.enum(CAP_COLOURS, { error: errorKey("validation.capColour") }),
  date: text(50, "fields.date"),
  coach: text(200, "fields.coach"),
  doctor: text(200, "fields.doctor"),
  assistant_coach: text(200, "fields.assistantCoach"),
  team_leader: text(200, "fields.teamLeader"),
  ball_thrower: text(200, "fields.ballThrower"),
  players: z
    .array(playerSchema)
    .min(1, errorKey("validation.minPlayers"))
    .max(MAX_PLAYERS, errorKey("validation.maxPlayers", { max: MAX_PLAYERS }))
    .superRefine((players, ctx) => {
      const seenCaps = new Set<number>();
      const seenNssz = new Set<string>();
      players.forEach((player, index) => {
        if (seenCaps.has(player.cap_number)) {
          ctx.addIssue({
            code: "custom",
            path: [index, "cap_number"],
            message: errorKey("validation.uniqueCapNumber"),
          });
        }
        seenCaps.add(player.cap_number);
        const nssz = player.nssz_number.toLowerCase();
        // Blank values are already reported as "required"; don't also call them duplicates.
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

export type LineupFormValues = z.infer<typeof lineupSchema>;

/** The smallest cap number from 1 to 15 that no row uses yet, or `undefined` when all are taken. */
export function nextFreeCapNumber(used: readonly number[]): number | undefined {
  for (let n = 1; n <= MAX_PLAYERS; n++) {
    if (!used.includes(n)) return n;
  }
  return undefined;
}
