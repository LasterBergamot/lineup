import { decodeError } from "@/i18n/error-key";
import { lineupSchema, nextFreeCapNumber } from "@/features/lineup/schema";

const valid = {
  match: "SZVTK - Csongrád",
  division: "OB II.",
  team_name: "SZVTK",
  cap: "Fehér" as const,
  date: "2024. 12. 21.",
  coach: "A",
  doctor: "B",
  assistant_coach: "C",
  team_leader: "D",
  ball_thrower: "E",
  players: [
    { cap_number: 1, name: "Török András", nssz_number: "MVLSZ1" },
    { cap_number: 2, name: "Kovács Béla", nssz_number: "MVLSZ2" },
  ],
};

/**
 * The schema emits error keys (translated later by `Field`), so the tests read them as
 * `path: key` or `path: key(params)` and need no language.
 */
function messages(input: unknown): string[] {
  const result = lineupSchema.safeParse(input);
  if (result.success) return [];
  return result.error.issues.map((issue) => {
    const { key, params } = decodeError(issue.message)!;
    const args = Object.values(params).join(", ");
    return `${issue.path.join(".")}: ${key}${args ? `(${args})` : ""}`;
  });
}

describe("lineupSchema", () => {
  it("accepts a complete lineup and trims the text", () => {
    const result = lineupSchema.parse({ ...valid, match: "  Final  " });
    expect(result.match).toBe("Final");
  });

  it("requires every text field, treating whitespace as empty", () => {
    expect(messages({ ...valid, coach: "   " })).toEqual([
      "coach: validation.required(fields.coach)",
    ]);
  });

  it("mirrors the API's maximum lengths", () => {
    expect(messages({ ...valid, division: "x".repeat(101) })).toEqual([
      "division: validation.tooLong(fields.division, 100)",
    ]);
    expect(lineupSchema.safeParse({ ...valid, match: "x".repeat(200) }).success).toBe(true);
  });

  it.each(["tab\there", "line\nbreak", "nul\u0000", "￾"])(
    "rejects control characters and noncharacters (%j)",
    (value) => {
      expect(messages({ ...valid, match: value })).toEqual([
        "match: validation.unsupportedCharacters(fields.match)",
      ]);
    },
  );

  it("only accepts the two cap colours", () => {
    expect(messages({ ...valid, cap: "Piros" })).toEqual(["cap: validation.capColour"]);
  });

  it("needs between 1 and 15 players", () => {
    expect(messages({ ...valid, players: [] })).toEqual(["players: validation.minPlayers"]);
    const sixteen = Array.from({ length: 16 }, (_, i) => ({
      cap_number: (i % 15) + 1,
      name: `P${i}`,
      nssz_number: `N${i}`,
    }));
    expect(messages({ ...valid, players: sixteen })).toContain(
      "players: validation.maxPlayers(15)",
    );
  });

  it.each([0, 16, 1.5, Number.NaN])("rejects cap number %s", (cap_number) => {
    const players = [{ cap_number, name: "A", nssz_number: "N" }];
    expect(messages({ ...valid, players })).toEqual(["players.0.cap_number: validation.capNumber"]);
  });

  it("flags a repeated cap number on the later row", () => {
    const players = [
      { cap_number: 3, name: "A", nssz_number: "N1" },
      { cap_number: 3, name: "B", nssz_number: "N2" },
    ];
    expect(messages({ ...valid, players })).toEqual([
      "players.1.cap_number: validation.uniqueCapNumber",
    ]);
  });

  it("flags a repeated NSSZ number, ignoring case", () => {
    const players = [
      { cap_number: 1, name: "A", nssz_number: "mvlsz1" },
      { cap_number: 2, name: "B", nssz_number: "MVLSZ1" },
    ];
    expect(messages({ ...valid, players })).toEqual([
      "players.1.nssz_number: validation.uniqueNssz",
    ]);
  });
});

describe("lineupSchema blank NSSZ numbers", () => {
  it("reports blanks as required only, not also as duplicates", () => {
    const players = [
      { cap_number: 1, name: "A", nssz_number: "" },
      { cap_number: 2, name: "B", nssz_number: "" },
    ];
    expect(messages({ ...valid, players })).toEqual([
      "players.0.nssz_number: validation.required(fields.nsszNumber)",
      "players.1.nssz_number: validation.required(fields.nsszNumber)",
    ]);
  });
});

describe("nextFreeCapNumber", () => {
  it("returns the smallest unused number", () => {
    expect(nextFreeCapNumber([])).toBe(1);
    expect(nextFreeCapNumber([1, 2, 4])).toBe(3);
  });

  it("returns undefined once all 15 are used", () => {
    expect(nextFreeCapNumber(Array.from({ length: 15 }, (_, i) => i + 1))).toBeUndefined();
  });
});
