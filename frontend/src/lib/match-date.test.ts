import { composeMatchDate, matchDateSchema, matchTimeSchema, todayIso } from "@/lib/match-date";

describe("todayIso", () => {
  it("is the local calendar day, zero-padded", () => {
    expect(todayIso(new Date(2026, 0, 5, 12))).toBe("2026-01-05");
    expect(todayIso(new Date(2026, 10, 24, 23, 59, 59))).toBe("2026-11-24");
    expect(todayIso(new Date(2026, 10, 25, 0, 0, 0))).toBe("2026-11-25");
  });

  it("reads the clock when called, defaulting to now", () => {
    vi.useFakeTimers({ now: new Date(2027, 1, 3, 8) });
    expect(todayIso()).toBe("2027-02-03");
    vi.useRealTimers();
  });
});

describe("composeMatchDate", () => {
  it("prints YYYY. MM. DD., with HH:MM only when a time is set", () => {
    expect(composeMatchDate("2026-11-24", "")).toBe("2026. 11. 24.");
    expect(composeMatchDate("2026-11-24", "18:30")).toBe("2026. 11. 24. 18:30");
  });
});

describe("matchDateSchema and matchTimeSchema", () => {
  it.each(["2026-11-24", "2028-02-29"])("accepts the date %s", (value) => {
    expect(matchDateSchema.safeParse(value).success).toBe(true);
  });

  it.each(["", "2026-13-01", "2027-02-29", "2026-11-31", "24.11.2026"])(
    "rejects the date %j",
    (value) => {
      expect(matchDateSchema.safeParse(value).success).toBe(false);
    },
  );

  it.each(["", "00:00", "18:30", "23:59"])("accepts the time %j", (value) => {
    expect(matchTimeSchema.safeParse(value).success).toBe(true);
  });

  it.each(["24:00", "18:60", "6:30", "18:30:15"])("rejects the time %j", (value) => {
    expect(matchTimeSchema.safeParse(value).success).toBe(false);
  });
});
