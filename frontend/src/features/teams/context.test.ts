import { renderHook } from "@testing-library/react";
import { useTeams } from "@/features/teams/context";

describe("useTeams", () => {
  it("refuses to run outside TeamsProvider", () => {
    // React logs the error it rethrows; keep the test output clean.
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      expect(() => renderHook(() => useTeams())).toThrow(
        "useTeams must be used inside TeamsProvider",
      );
    } finally {
      log.mockRestore();
    }
  });
});
