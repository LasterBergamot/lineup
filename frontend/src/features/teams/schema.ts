import { z } from "zod";
import { cleanText } from "@/lib/clean-text";

/** The "create a team" form; the name limit matches the API's `CleanStr120`. */
export const teamFormSchema = z.object({
  name: cleanText(120, "fields.teamName"),
  isPublic: z.boolean(),
});

export type TeamFormValues = z.infer<typeof teamFormSchema>;
