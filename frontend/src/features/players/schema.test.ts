import { decodeError } from "@/i18n/error-key";
import { playerFormSchema } from "@/features/players/schema";

/** The schema emits error keys, so the tests read them as `path: key(params)` and need no language. */
function messages(input: unknown): string[] {
  const result = playerFormSchema.safeParse(input);
  if (result.success) return [];
  return result.error.issues.map((issue) => {
    const { key, params } = decodeError(issue.message)!;
    const args = Object.values(params).join(", ");
    return `${issue.path.join(".")}: ${key}${args ? `(${args})` : ""}`;
  });
}

describe("playerFormSchema", () => {
  it("accepts a name and an NSSZ number, trimmed", () => {
    expect(playerFormSchema.parse({ name: "  Török András ", nsszNumber: " MVLSZ1 " })).toEqual({
      name: "Török András",
      nsszNumber: "MVLSZ1",
    });
  });

  it("requires both fields, also when only spaces are given", () => {
    expect(messages({ name: "   ", nsszNumber: "" })).toEqual([
      "name: validation.required(fields.name)",
      "nsszNumber: validation.required(fields.nsszNumber)",
    ]);
  });

  it("caps the lengths at the API's limits", () => {
    expect(messages({ name: "a".repeat(200), nsszNumber: "1".repeat(50) })).toEqual([]);
    expect(messages({ name: "a".repeat(201), nsszNumber: "1".repeat(51) })).toEqual([
      "name: validation.tooLong(fields.name, 200)",
      "nsszNumber: validation.tooLong(fields.nsszNumber, 50)",
    ]);
  });

  it("rejects control characters", () => {
    expect(messages({ name: "Ann\u0000", nsszNumber: "N\u00071" })).toEqual([
      "name: validation.unsupportedCharacters(fields.name)",
      "nsszNumber: validation.unsupportedCharacters(fields.nsszNumber)",
    ]);
  });
});
