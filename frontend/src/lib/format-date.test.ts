import { formatDateTime, parseApiDate } from "@/lib/format-date";

describe("parseApiDate", () => {
  it("reads a value without a zone as UTC", () => {
    expect(parseApiDate("2026-10-05T10:00:00").toISOString()).toBe("2026-10-05T10:00:00.000Z");
  });

  it.each(["2026-10-05T10:00:00Z", "2026-10-05T12:00:00+02:00", "2026-10-05T12:00:00+0200"])(
    "keeps the zone of %s",
    (value) => {
      expect(parseApiDate(value).toISOString()).toBe("2026-10-05T10:00:00.000Z");
    },
  );
});

describe("formatDateTime", () => {
  it("formats in the given language", () => {
    expect(formatDateTime("2026-10-05T10:00:00Z", "en")).toMatch(/Oct/);
    expect(formatDateTime("2026-10-05T10:00:00Z", "hu")).toMatch(/okt/);
  });
});
