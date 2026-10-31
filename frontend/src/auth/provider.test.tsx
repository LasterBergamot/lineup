import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { AuthProvider } from "@/auth/provider";
import { getSupabase } from "@/auth/supabase";
import { testQueryClient } from "@/test/auth";

vi.mock("@/auth/supabase", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/auth/supabase")>()),
  getSupabase: vi.fn(),
}));

describe("AuthProvider", () => {
  it("lets an unexpected client-creation failure surface instead of hiding it as 'unconfigured'", () => {
    vi.mocked(getSupabase).mockImplementation(() => {
      throw new Error("kaboom");
    });
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <QueryClientProvider client={testQueryClient()}>
          <AuthProvider>
            <p>child</p>
          </AuthProvider>
        </QueryClientProvider>,
      ),
    ).toThrow("kaboom");
    spy.mockRestore();
  });
});
