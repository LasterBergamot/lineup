import { z } from "zod";
import { errorKey, type ErrorParams } from "@/i18n/error-key";

/** Control characters, surrogates and U+FFFE/U+FFFF: the backend rejects them (python-docx can't write them). */
const UNSAFE_CHARACTERS = /[\p{Cc}\p{Cs}\uFFFE\uFFFF]/u;

/**
 * Required text: trimmed, non-empty, length-capped and free of control characters. This mirrors
 * the backend's `CleanStr*` types (`backend/lineup/common/types.py`), so a form catches what the
 * API would answer with a 422, before a slow request is made. `field` is the `fields.*` locale
 * key of the label; the messages are error keys (see `errorKey`) that `Field` translates.
 */
export function cleanText(max: number, field: NonNullable<ErrorParams["field"]>) {
  return z
    .string()
    .trim()
    .min(1, errorKey("validation.required", { field }))
    .max(max, errorKey("validation.tooLong", { field, max }))
    .refine(
      (value) => !UNSAFE_CHARACTERS.test(value),
      errorKey("validation.unsupportedCharacters", { field }),
    );
}

/**
 * Optional text: like {@link cleanText}, but a blank value is allowed (the form sends it as
 * "not provided"). It still has to fit the length cap and be free of control characters.
 */
export function optionalCleanText(max: number, field: NonNullable<ErrorParams["field"]>) {
  return z
    .string()
    .trim()
    .max(max, errorKey("validation.tooLong", { field, max }))
    .refine(
      (value) => !UNSAFE_CHARACTERS.test(value),
      errorKey("validation.unsupportedCharacters", { field }),
    );
}
