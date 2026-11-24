import { sortByName } from "@/lib/sort-by-name";

const player = (name: string, nssz_number = "MVLSZ0") => ({ name, nssz_number });
const names = (rows: { name: string }[]) => rows.map((row) => row.name);

describe("sortByName", () => {
  it("follows the Hungarian alphabet: digraphs and accents sort with their letters", () => {
    const rows = [
      "Tóth",
      "Sándor",
      "Szabó",
      "Zsolt",
      "Cseh",
      "Csaba",
      "Dóra",
      "Dzsenifer",
      "Gábor",
      "Gyula",
      "Csongor",
    ];
    expect(names(sortByName(rows.map((name) => player(name))))).toEqual([
      "Csaba",
      "Cseh",
      "Csongor",
      "Dóra",
      "Dzsenifer",
      "Gábor",
      "Gyula",
      "Sándor",
      "Szabó",
      "Tóth",
      "Zsolt",
    ]);
  });

  it("puts Cs after C and Sz after S, as Hungarian does", () => {
    const rows = [player("Sz"), player("Cs"), player("C"), player("S")];
    expect(names(sortByName(rows))).toEqual(["C", "Cs", "S", "Sz"]);
  });

  it("breaks ties by the NSSZ number, so the order is stable", () => {
    const rows = [player("Kovács", "MVLSZ2"), player("Kovacs", "MVLSZ1")];
    expect(sortByName(rows).map((row) => row.nssz_number)).toEqual(["MVLSZ1", "MVLSZ2"]);
  });

  it("returns a new array and leaves the input in the API order", () => {
    const input = [player("Nagy"), player("Kovács")];
    const sorted = sortByName(input);
    expect(sorted).not.toBe(input);
    expect(names(input)).toEqual(["Nagy", "Kovács"]);
  });
});
