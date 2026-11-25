import { z } from "zod";
import { errorKey } from "@/i18n/error-key";

/** `YYYY-MM-DD`, what `<input type="date">` holds (an empty string when nothing valid is typed). */
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** `HH:MM`, what `<input type="time">` holds (seconds only when the input has a `step` below 60). */
const ISO_TIME = /^([01]\d|2[0-3]):[0-5]\d$/;

/**
 * Today's date in the browser's local time zone as `YYYY-MM-DD`: the default of the match date.
 * It is read when a form is built, not at import time, so a tab left open overnight still starts
 * the next new lineup on the right day. `now` exists for tests.
 */
export function todayIso(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * The match date as the sheet prints it: `YYYY. MM. DD.`, plus ` HH:MM` when a time is set. This
 * is the same text the API composes from `match_date`/`match_time`; the Quick sheet and the
 * creator's preview need it client-side because their request carries only the printed `date`.
 * `date` is `YYYY-MM-DD` (validate with {@link matchDateSchema} first); `time` is `""` or `HH:MM`.
 */
export function composeMatchDate(date: string, time: string): string {
  const printed = date.replace(ISO_DATE, "$1. $2. $3.");
  return time ? `${printed} ${time}` : printed;
}

/** The printed text {@link composeMatchDate} makes: `YYYY. MM. DD.`, optionally ` HH:MM`. */
const PRINTED = /^(\d{4})\. (\d{2})\. (\d{2})\.(?: ([01]\d|2[0-3]):([0-5]\d))?$/;

/**
 * Reads a printed match date back into the inputs' values: the reverse of
 * {@link composeMatchDate}. Editing a saved lineup (#290) needs it for one stored before the
 * structured `match_date` existed (#287), which has only the printed `date` text. Returns `null`
 * for any other text (an old lineup may hold free text), so the form starts with an empty date
 * and asks for one. The day is not checked here: {@link matchDateSchema} does that on save.
 */
export function parseMatchDate(printed: string): { date: string; time: string } | null {
  const [, year, month, day, hour, minute] = PRINTED.exec(printed.trim()) ?? [];
  if (!year) return null;
  return { date: `${year}-${month}-${day}`, time: hour ? `${hour}:${minute}` : "" };
}

/**
 * The required match date from a date input. It must be a real calendar day; an empty value
 * (cleared or half-typed) is "required", like the other required fields.
 */
export const matchDateSchema = z.string().refine(
  (value) => {
    const [, year, month, day] = ISO_DATE.exec(value) ?? [];
    if (!year) return false;
    const date = new Date(Number(year), Number(month) - 1, Number(day));
    return date.getMonth() === Number(month) - 1 && date.getDate() === Number(day);
  },
  errorKey("validation.required", { field: "fields.date" }),
);

/** The optional start time from a time input: blank, or `HH:MM`. */
export const matchTimeSchema = z.string().refine((value) => value === "" || ISO_TIME.test(value), {
  message: errorKey("validation.required", { field: "fields.time" }),
});
