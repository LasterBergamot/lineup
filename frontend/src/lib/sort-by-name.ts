/**
 * Hungarian alphabetical order for players (#283). `Intl.Collator("hu")` is built into the
 * browser, so nothing is fetched or stored: `cs`, `dz`, `gy`, `ly`, `ny`, `sz`, `ty` and `zs` sort
 * as single letters and accented vowels sort with their base letter. `sensitivity: "base"` makes
 * `Kovács` and `Kovacs` equal, so the NSSZ number breaks the tie and the order does not change
 * between renders. Returns a new array: the API order (and the query cache) stays untouched.
 */
const collator = new Intl.Collator("hu", { sensitivity: "base" });

export function sortByName<T extends { name: string; nssz_number: string }>(
  rows: readonly T[],
): T[] {
  return [...rows].sort(
    (a, b) => collator.compare(a.name, b.name) || collator.compare(a.nssz_number, b.nssz_number),
  );
}
