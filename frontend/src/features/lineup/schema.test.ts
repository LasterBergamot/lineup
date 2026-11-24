import { decodeError } from "@/i18n/error-key";
import { capRows } from "@/features/lineup/cap-rows";
import {
  emptyQuickSheetValues,
  lineupSchema,
  toQuickSheetRequest,
  type LineupFormValues,
} from "@/features/lineup/schema";

/** The 15 cap rows, with the given ones filled in by cap number. */
function rows(filled: Record<number, { name: string; nssz_number: string }> = {}) {
  return capRows((cap_number) => ({
    cap_number,
    name: "",
    nssz_number: "",
    ...filled[cap_number],
  }));
}

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
  players: rows({
    1: { name: "Török András", nssz_number: "MVLSZ1" },
    2: { name: "Kovács Béla", nssz_number: "MVLSZ2" },
  }),
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

  it("needs a filled row and at most 15 rows", () => {
    expect(messages({ ...valid, players: rows() })).toEqual(["players: validation.minPlayers"]);
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

  it("flags the missing half of a half-filled row", () => {
    const players = rows({
      1: { name: "A", nssz_number: "N1" },
      4: { name: "B", nssz_number: "" },
    });
    expect(messages({ ...valid, players })).toEqual([
      "players.3.nssz_number: validation.required(fields.nsszNumber)",
    ]);
  });

  it("flags a repeated NSSZ number, ignoring case", () => {
    const players = rows({
      1: { name: "A", nssz_number: "mvlsz1" },
      2: { name: "B", nssz_number: "MVLSZ1" },
    });
    expect(messages({ ...valid, players })).toEqual([
      "players.1.nssz_number: validation.uniqueNssz",
    ]);
  });
});

describe("lineupSchema blank NSSZ numbers", () => {
  it("reports blanks as required only, not also as duplicates", () => {
    const players = rows({ 1: { name: "A", nssz_number: "" }, 2: { name: "B", nssz_number: "" } });
    expect(messages({ ...valid, players })).toEqual([
      "players.0.nssz_number: validation.required(fields.nsszNumber)",
      "players.1.nssz_number: validation.required(fields.nsszNumber)",
    ]);
  });
});

describe("emptyQuickSheetValues", () => {
  it("opens with white caps and the 15 empty cap rows", () => {
    expect(emptyQuickSheetValues()).toEqual({ cap: "Fehér", players: rows() });
  });
});

describe("toQuickSheetRequest", () => {
  it("sends the form values with only the filled rows", () => {
    const values = lineupSchema.parse({
      ...valid,
      players: rows({ 5: { name: " Kiss Ádám ", nssz_number: "N5" } }),
    }) as LineupFormValues;
    expect(toQuickSheetRequest(values)).toEqual({
      ...valid,
      players: [{ cap_number: 5, name: "Kiss Ádám", nssz_number: "N5" }],
    });
  });
});
