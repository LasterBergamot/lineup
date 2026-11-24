import type { z } from "zod";
import { errorKey } from "@/i18n/error-key";
import { cleanText } from "@/lib/clean-text";

/** A lineup has at most this many players, one per cap number from 1 to this value. */
export const MAX_PLAYERS = 15;

/**
 * One cap row of the creator or the Quick sheet. Both forms always hold exactly
 * {@link MAX_PLAYERS} rows, row `i` wearing cap `i + 1`, so the form reads like the printed sheet
 * and a duplicate or missing cap number cannot happen. `playerId` only exists in the creator: the
 * roster player picked for the row, or `""` for one typed in by hand.
 */
export interface CapRow {
  cap_number: number;
  playerId?: string;
  name: string;
  nssz_number: string;
}

/** One player as the API's `players[]` takes them. */
export interface RequestPlayer {
  cap_number: number;
  name: string;
  nssz_number: string;
}

const NAME = cleanText(200, "fields.name");
const NSSZ = cleanText(50, "fields.nsszNumber");

/** The fixed rows, caps 1 to 15 in order, each built by `make` from its cap number. */
export function capRows<T>(make: (capNumber: number) => T): T[] {
  return Array.from({ length: MAX_PLAYERS }, (_, index) => make(index + 1));
}

/**
 * A row with no roster pick and no typed name or NSSZ number (blanks only count as empty). Empty
 * rows are left out of every request; a row with anything in it must be complete.
 */
export function isEmptyRow(row: CapRow): boolean {
  return !row.playerId && !row.name.trim() && !row.nssz_number.trim();
}

/** The rows that reach a request, in cap order. */
export function filledRows<T extends CapRow>(rows: readonly T[]): T[] {
  return rows.filter((row) => !isEmptyRow(row));
}

/** The filled rows as the API's `players[]`, with typed-in text trimmed like the form's other fields. */
export function requestPlayers(rows: readonly CapRow[]): RequestPlayer[] {
  return filledRows(rows).map((row) => ({
    cap_number: row.cap_number,
    name: row.name.trim(),
    nssz_number: row.nssz_number.trim(),
  }));
}

/**
 * The validation both forms share, for a Zod `superRefine` on the `players` array. Empty rows are
 * skipped. A typed-in row needs a valid name and NSSZ number (a half-filled row is a field error);
 * a roster pick is already valid. An NSSZ number may appear only once, and at least one row must
 * be filled, otherwise `validation.minPlayers` is raised on the array itself.
 */
export function checkCapRows(rows: readonly CapRow[], ctx: z.RefinementCtx): void {
  const seenNssz = new Set<string>();
  let filled = 0;
  rows.forEach((row, index) => {
    if (isEmptyRow(row)) return;
    filled += 1;
    if (!row.playerId) {
      for (const [field, rule] of [
        ["name", NAME],
        ["nssz_number", NSSZ],
      ] as const) {
        const result = rule.safeParse(row[field]);
        if (!result.success) {
          ctx.addIssue({
            code: "custom",
            path: [index, field],
            message: result.error.issues[0]!.message,
          });
        }
      }
    }
    const nssz = row.nssz_number.trim().toLowerCase();
    // A blank one is already reported as "required"; don't also call it a duplicate.
    if (nssz && seenNssz.has(nssz)) {
      ctx.addIssue({
        code: "custom",
        path: [index, "nssz_number"],
        message: errorKey("validation.uniqueNssz"),
      });
    }
    seenNssz.add(nssz);
  });
  if (filled === 0) {
    ctx.addIssue({ code: "custom", path: [], message: errorKey("validation.minPlayers") });
  }
}

/**
 * Maps a server 422 path onto the form. The request only carries the filled rows, so the API's
 * `players.<n>` is the n-th filled row, not form row n: this rewrites it to that row's index.
 * Any other path is returned unchanged.
 */
export function rowPath(path: string, rows: readonly CapRow[]): string {
  const formIndexes = rows.flatMap((row, index) => (isEmptyRow(row) ? [] : [index]));
  return path.replace(/^players\.(\d+)(?=\.|$)/, (whole, n: string) => {
    const index = formIndexes[Number(n)];
    return index === undefined ? whole : `players.${index}`;
  });
}
