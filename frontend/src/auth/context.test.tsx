import { renderHook } from "@testing-library/react";
import { useAuth } from "@/auth/context";

describe("useAuth", () => {
  it("refuses to work outside AuthProvider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow("useAuth must be used inside AuthProvider");
    spy.mockRestore();
  });
});
