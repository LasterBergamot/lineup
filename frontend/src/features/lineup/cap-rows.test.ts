import { z } from "zod";
import {
  capRows,
  checkCapRows,
  filledRows,
  isEmptyRow,
  MAX_PLAYERS,
  requestPlayers,
  rowPath,
  type CapRow,
} from "@/features/lineup/cap-rows";
import { decodeError } from "@/i18n/error-key";

/** The 15 rows with the given ones filled in by cap number. */
function rows(filled: Partial<Record<number, Partial<CapRow>>> = {}): CapRow[] {
  return capRows((cap_number) => ({
    cap_number,
    playerId: "",
    name: "",
    nssz_number: "",
    ...filled[cap_number],
  }));
}

const schema = z.array(z.custom<CapRow>()).superRefine(checkCapRows);

/** Errors as `path: key(params)`, so the tests need no language. */
function messages(input: CapRow[]): string[] {
  const result = schema.safeParse(input);
  if (result.success) return [];
  return result.error.issues.map((issue) => {
    const { key, params } = decodeError(issue.message)!;
    const args = Object.values(params).join(", ");
    return `${issue.path.join(".")}: ${key}${args ? `(${args})` : ""}`;
  });
}

describe("capRows", () => {
  it("builds one row per cap number, 1 to 15 in order", () => {
    expect(capRows((n) => n)).toEqual(Array.from({ length: MAX_PLAYERS }, (_, i) => i + 1));
  });
});

describe("isEmptyRow / filledRows", () => {
  it("treats a row with only blanks as empty", () => {
    expect(isEmptyRow({ cap_number: 1, name: " ", nssz_number: "\t" })).toBe(true);
    expect(isEmptyRow({ cap_number: 1, playerId: "", name: "", nssz_number: "" })).toBe(true);
  });

  it("counts a roster pick, a name or an NSSZ number as filled", () => {
    expect(isEmptyRow({ cap_number: 1, playerId: "p-1", name: "", nssz_number: "" })).toBe(false);
    expect(isEmptyRow({ cap_number: 1, name: "A", nssz_number: "" })).toBe(false);
    expect(isEmptyRow({ cap_number: 1, name: "", nssz_number: "N" })).toBe(false);
  });

  it("keeps the filled rows in cap order", () => {
    const filled = filledRows(rows({ 7: { name: "B" }, 2: { name: "A" } }));
    expect(filled.map((row) => row.cap_number)).toEqual([2, 7]);
  });
});

describe("requestPlayers", () => {
  it("sends only the filled rows, trimmed, without the roster id", () => {
    const players = requestPlayers(
      rows({
        3: { name: " Kiss Ádám ", nssz_number: " N3 " },
        9: { playerId: "p", name: "B", nssz_number: "N9" },
      }),
    );
    expect(players).toEqual([
      { cap_number: 3, name: "Kiss Ádám", nssz_number: "N3" },
      { cap_number: 9, name: "B", nssz_number: "N9" },
    ]);
  });
});

describe("checkCapRows", () => {
  it("accepts filled rows among empty ones", () => {
    expect(messages(rows({ 4: { name: "A", nssz_number: "N1" } }))).toEqual([]);
  });

  it("asks for at least one filled row", () => {
    expect(messages(rows())).toEqual([": validation.minPlayers"]);
  });

  it("flags the missing half of a half-filled row", () => {
    expect(messages(rows({ 2: { name: "A" }, 5: { nssz_number: "N5" } }))).toEqual([
      "1.nssz_number: validation.required(fields.nsszNumber)",
      "4.name: validation.required(fields.name)",
    ]);
  });

  it("checks typed-in text but trusts a roster pick", () => {
    expect(
      messages(rows({ 1: { name: "a\u0000b", nssz_number: "N1" }, 2: { playerId: "p-1" } })),
    ).toEqual(["0.name: validation.unsupportedCharacters(fields.name)"]);
  });

  it("flags a repeated NSSZ number (any case, any spacing) on the later row", () => {
    expect(
      messages(
        rows({
          1: { name: "A", nssz_number: "mvlsz1" },
          6: { playerId: "p", nssz_number: " MVLSZ1" },
        }),
      ),
    ).toEqual(["5.nssz_number: validation.uniqueNssz"]);
  });
});

describe("rowPath", () => {
  const sent = rows({ 3: { name: "A" }, 8: { name: "B" } });

  it("maps the n-th sent player onto its form row", () => {
    expect(rowPath("players.0.name", sent)).toBe("players.2.name");
    expect(rowPath("players.1", sent)).toBe("players.7");
  });

  it("leaves other paths and unknown indexes alone", () => {
    expect(rowPath("players", sent)).toBe("players");
    expect(rowPath("players.5.name", sent)).toBe("players.5.name");
    expect(rowPath("coach", sent)).toBe("coach");
  });
});
