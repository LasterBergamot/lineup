import { creatorSchema } from "@/features/creator/schema";
import { emptyValues } from "@/features/creator/resolve";
import { decodeError } from "@/i18n/error-key";

/** Errors as `path: key(params)`, so the tests need no language. */
function messages(input: unknown): string[] {
  const result = creatorSchema.safeParse(input);
  if (result.success) return [];
  return result.error.issues.map((issue) => {
    const decoded = decodeError(issue.message)!;
    const args = Object.values(decoded.params).join(", ");
    return `${issue.path.join(".")}: ${decoded.key}${args ? `(${args})` : ""}`;
  });
}

const valid = () => ({
  ...emptyValues(),
  opponent: "Csongrád",
  division: "OB I.",
  date: "2026. 11. 1.",
  coach: "Kovács",
  players: [{ cap_number: 1, playerId: "", name: "Nagy Bence", nssz_number: "MVLSZ1" }],
});

describe("creatorSchema", () => {
  it("accepts a minimal lineup, with the optional fields blank", () => {
    expect(messages(valid())).toEqual([]);
  });

  it("requires the opponent, division, date, coach and cap colour", () => {
    expect(
      messages({ ...valid(), opponent: " ", division: "", date: "", coach: "", cap: "Zöld" }),
    ).toEqual([
      "opponent: validation.required(fields.opponent)",
      "division: validation.required(fields.division)",
      "cap: validation.capColour",
      "date: validation.required(fields.date)",
      "coach: validation.required(fields.coach)",
    ]);
  });

  it("limits the optional fields but lets them be blank", () => {
    expect(messages({ ...valid(), doctor: "x".repeat(201), match_name: "a\u0000b" })).toEqual([
      "match_name: validation.unsupportedCharacters(fields.match)",
      "doctor: validation.tooLong(fields.doctor, 200)",
    ]);
  });

  it("checks typed-in players but trusts the ones picked from the roster", () => {
    const players = [
      { cap_number: 1, playerId: "", name: "", nssz_number: " " },
      { cap_number: 2, playerId: "p-1", name: "", nssz_number: "" },
    ];
    expect(messages({ ...valid(), players })).toEqual([
      "players.0.name: validation.required(fields.name)",
      "players.0.nssz_number: validation.required(fields.nsszNumber)",
    ]);
  });

  it("needs 1 to 15 players", () => {
    expect(messages({ ...valid(), players: [] })).toEqual(["players: validation.minPlayers"]);
    const many = Array.from({ length: 16 }, (_, i) => ({
      cap_number: (i % 15) + 1,
      playerId: "",
      name: `P${i}`,
      nssz_number: `N${i}`,
    }));
    expect(messages({ ...valid(), players: many })).toContain("players: validation.maxPlayers(15)");
  });

  it("rejects a repeated cap number or NSSZ number (any case) on the later row", () => {
    const players = [
      { cap_number: 3, playerId: "", name: "A", nssz_number: "mvlsz1" },
      { cap_number: 3, playerId: "p-2", name: "B", nssz_number: "MVLSZ1" },
    ];
    expect(messages({ ...valid(), players })).toEqual([
      "players.1.cap_number: validation.uniqueCapNumber",
      "players.1.nssz_number: validation.uniqueNssz",
    ]);
  });
});
