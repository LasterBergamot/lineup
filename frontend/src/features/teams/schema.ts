import { z } from "zod";
import { cleanText, optionalCleanText } from "@/lib/clean-text";

/** The "create a team" form; the name limit matches the API's `CleanStr120`, the optional
 * default division the API's `CleanStr100`. */
export const teamFormSchema = z.object({
  name: cleanText(120, "fields.teamName"),
  division: optionalCleanText(100, "fields.division"),
  isPublic: z.boolean(),
});

export type TeamFormValues = z.infer<typeof teamFormSchema>;
