import { cn } from "@/lib/utils";

describe("cn", () => {
  it("joins truthy class names and drops falsy ones", () => {
    const off = false;
    expect(cn("a", off && "b", undefined, "c")).toBe("a c");
  });

  it("lets a later Tailwind utility override a conflicting earlier one", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });
});
