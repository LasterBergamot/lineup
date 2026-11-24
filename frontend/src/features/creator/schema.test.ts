import { creatorSchema, type CreatorValues } from "@/features/creator/schema";
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
  match_date: "2026-11-01",
  coach: "Kovács",
  players: rows({ 1: { name: "Nagy Bence", nssz_number: "MVLSZ1" } }),
});

/** The 15 cap rows, with the given ones filled in by cap number. */
function rows(filled: Record<number, Partial<CreatorValues["players"][number]>> = {}) {
  return emptyValues().players.map((row) => ({ ...row, ...filled[row.cap_number] }));
}

describe("creatorSchema", () => {
  it("accepts a minimal lineup, with the optional fields blank", () => {
    expect(messages(valid())).toEqual([]);
  });

  it("requires the opponent, division, date, coach and cap colour", () => {
    expect(
      messages({ ...valid(), opponent: " ", division: "", match_date: "", coach: "", cap: "Zöld" }),
    ).toEqual([
      "opponent: validation.required(fields.opponent)",
      "division: validation.required(fields.division)",
      "cap: validation.capColour",
      "match_date: validation.required(fields.date)",
      "coach: validation.required(fields.coach)",
    ]);
  });

  it("accepts only a real calendar day and a blank or HH:MM time", () => {
    expect(messages({ ...valid(), match_date: "2026-02-30" })).toEqual([
      "match_date: validation.required(fields.date)",
    ]);
    expect(messages({ ...valid(), match_date: "1.11.2026" })).toEqual([
      "match_date: validation.required(fields.date)",
    ]);
    expect(messages({ ...valid(), match_time: "18:30" })).toEqual([]);
    expect(messages({ ...valid(), match_time: "24:00" })).toEqual([
      "match_time: validation.required(fields.time)",
    ]);
  });

  it("limits the optional fields but lets them be blank", () => {
    expect(messages({ ...valid(), doctor: "x".repeat(201), match_name: "a\u0000b" })).toEqual([
      "match_name: validation.unsupportedCharacters(fields.match)",
      "doctor: validation.tooLong(fields.doctor, 200)",
    ]);
  });

  it("checks typed-in players but trusts the ones picked from the roster", () => {
    const players = rows({ 1: { name: "a\u0000b", nssz_number: "N1" }, 2: { playerId: "p-1" } });
    expect(messages({ ...valid(), players })).toEqual([
      "players.0.name: validation.unsupportedCharacters(fields.name)",
    ]);
  });

  it("skips empty rows, flags a half-filled one and needs at least one filled row", () => {
    expect(messages({ ...valid(), players: rows() })).toEqual(["players: validation.minPlayers"]);
    expect(messages({ ...valid(), players: rows({ 9: { name: "Kiss" } }) })).toEqual([
      "players.8.nssz_number: validation.required(fields.nsszNumber)",
    ]);
  });

  it("allows at most 15 rows", () => {
    const many = Array.from({ length: 16 }, (_, i) => ({
      cap_number: (i % 15) + 1,
      playerId: "",
      name: `P${i}`,
      nssz_number: `N${i}`,
    }));
    expect(messages({ ...valid(), players: many })).toContain("players: validation.maxPlayers(15)");
  });

  it("rejects a repeated NSSZ number (any case) on the later row", () => {
    const players = rows({
      1: { name: "A", nssz_number: "mvlsz1" },
      3: { playerId: "p-2", name: "B", nssz_number: "MVLSZ1" },
    });
    expect(messages({ ...valid(), players })).toEqual([
      "players.2.nssz_number: validation.uniqueNssz",
    ]);
  });
});
