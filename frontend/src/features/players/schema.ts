import { z } from "zod";
import { cleanText } from "@/lib/clean-text";

/**
 * The add/edit player form. The limits mirror the API's `CleanStr200` (name) and `CleanStr50`
 * (NSSZ number). Uniqueness of NSSZ numbers is not checked here: the API allows duplicates on a
 * roster and only rejects them within one lineup.
 */
export const playerFormSchema = z.object({
  name: cleanText(200, "fields.name"),
  nsszNumber: cleanText(50, "fields.nsszNumber"),
});

export type PlayerFormValues = z.infer<typeof playerFormSchema>;
