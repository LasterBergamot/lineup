import { z } from "zod";
import { cleanText } from "@/lib/clean-text";

/**
 * The add/edit player form. The limits mirror the API's `CleanStr200` (name) and `CleanStr50`
 * (NSSZ number). Uniqueness is not checked here: the API answers 409 for an NSSZ number already on
 * the roster (the form shows it on that field), and the form itself warns about a repeated name.
 */
export const playerFormSchema = z.object({
  name: cleanText(200, "fields.name"),
  nsszNumber: cleanText(50, "fields.nsszNumber"),
});

export type PlayerFormValues = z.infer<typeof playerFormSchema>;
