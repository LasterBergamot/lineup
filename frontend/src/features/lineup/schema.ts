import { z } from "zod";
import { cleanText as text } from "@/lib/clean-text";

export const CAP_COLOURS = ["Fehér", "Kék"] as const;

export const MAX_PLAYERS = 15;

const playerSchema = z.object({
  cap_number: z
    .number({ error: "Enter a cap number from 1 to 15" })
    .int("Enter a cap number from 1 to 15")
    .min(1, "Enter a cap number from 1 to 15")
    .max(MAX_PLAYERS, "Enter a cap number from 1 to 15"),
  name: text(200, "Name"),
  nssz_number: text(50, "NSSZ number"),
});

/** The one-off lineup form; the shape is exactly the API's `LineupRequest`. */
export const lineupSchema = z.object({
  match: text(200, "Match"),
  division: text(100, "Division"),
  team_name: text(120, "Team name"),
  cap: z.enum(CAP_COLOURS, { error: "Choose a cap colour" }),
  date: text(50, "Date"),
  coach: text(200, "Coach"),
  doctor: text(200, "Doctor"),
  assistant_coach: text(200, "Assistant coach"),
  team_leader: text(200, "Team leader"),
  ball_thrower: text(200, "Ball thrower"),
  players: z
    .array(playerSchema)
    .min(1, "Add at least one player")
    .max(MAX_PLAYERS, `A lineup has at most ${MAX_PLAYERS} players`)
    .superRefine((players, ctx) => {
      const seenCaps = new Set<number>();
      const seenNssz = new Set<string>();
      players.forEach((player, index) => {
        if (seenCaps.has(player.cap_number)) {
          ctx.addIssue({
            code: "custom",
            path: [index, "cap_number"],
            message: "Cap numbers must be unique",
          });
        }
        seenCaps.add(player.cap_number);
        const nssz = player.nssz_number.toLowerCase();
        // Blank values are already reported as "required"; don't also call them duplicates.
        if (nssz && seenNssz.has(nssz)) {
          ctx.addIssue({
            code: "custom",
            path: [index, "nssz_number"],
            message: "NSSZ numbers must be unique",
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
