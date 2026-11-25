import { capFor, orderMatchName, sideOf, suggestMatchName } from "@/features/creator/home-away";

describe("home / away helpers", () => {
  it("maps is_home to the toggle and the cap colour", () => {
    expect(sideOf(true)).toBe("home");
    expect(sideOf(false)).toBe("away");
    expect(sideOf(null)).toBe("");
    expect(capFor(true)).toBe("Fehér");
    expect(capFor(false)).toBe("Kék");
  });

  it("suggests the match name home team first, and nothing without an opponent", () => {
    expect(suggestMatchName("SZVTK", " Csongrád ", true)).toBe("SZVTK - Csongrád");
    expect(suggestMatchName("SZVTK", "Csongrád", false)).toBe("Csongrád - SZVTK");
    expect(suggestMatchName("SZVTK", "  ", true)).toBe("");
  });

  it("puts the team on the right side of a typed 'A - B' name", () => {
    expect(orderMatchName("Csongrád - SZVTK", "SZVTK", true)).toBe("SZVTK - Csongrád");
    expect(orderMatchName("SZVTK - Csongrád", "szvtk", false)).toBe("Csongrád - SZVTK");
    expect(orderMatchName("SZVTK - Csongrád", "SZVTK", true)).toBe("SZVTK - Csongrád");
  });

  it("leaves any other name alone", () => {
    expect(orderMatchName("Derby", "SZVTK", true)).toBe("Derby");
    expect(orderMatchName("A - B", "SZVTK", true)).toBe("A - B");
    expect(orderMatchName("A - B - C", "A", true)).toBe("A - B - C");
    expect(orderMatchName("A - B", "", true)).toBe("A - B");
  });
});
