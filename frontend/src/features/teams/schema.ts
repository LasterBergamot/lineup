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

/** The owner's team settings: the create form plus the optional home venue (#296), the API's `CleanStr200`. */
export const teamSettingsSchema = teamFormSchema.extend({
  homeVenue: optionalCleanText(200, "fields.homeVenue"),
});

export type TeamSettingsValues = z.infer<typeof teamSettingsSchema>;
