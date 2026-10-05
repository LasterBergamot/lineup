import { z } from "zod";

/** Control characters, surrogates and U+FFFE/U+FFFF: the backend rejects them (python-docx can't write them). */
const UNSAFE_CHARACTERS = /[\p{Cc}\p{Cs}\uFFFE\uFFFF]/u;

/**
 * Required text: trimmed, non-empty, length-capped and free of control characters. This mirrors
 * the backend's `CleanStr*` types (`backend/lineup/common/types.py`), so a form catches what the
 * API would answer with a 422, before a slow request is made.
 */
export function cleanText(max: number, label: string) {
  return z
    .string()
    .trim()
    .min(1, `${label} is required`)
    .max(max, `${label} can be at most ${max} characters`)
    .refine((value) => !UNSAFE_CHARACTERS.test(value), `${label} contains unsupported characters`);
}
