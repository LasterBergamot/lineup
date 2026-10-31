/**
 * Reads a timestamp from the API. The backend stores UTC; SQLite hands it back without a zone
 * designator, which `Date` would read as local time, so a bare value is treated as UTC here.
 */
export function parseApiDate(value: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`);
}

/** An API timestamp as a short date and time in `language` (the UI language, `hu` or `en`). */
export function formatDateTime(value: string, language: string): string {
  return new Intl.DateTimeFormat(language, { dateStyle: "medium", timeStyle: "short" }).format(
    parseApiDate(value),
  );
}
