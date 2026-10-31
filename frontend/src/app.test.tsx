import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { App } from "@/app";

// The real health probe would call fetch; the root component must not touch the network here.
vi.mock("@/backend-status/health", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/backend-status/health")>()),
  probeHealth: vi.fn(async () => "ok"),
}));

beforeEach(() => {
  // Same state as a build without Supabase settings, whatever the local .env holds.
  vi.stubEnv("VITE_SUPABASE_URL", "");
  vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");
});

afterEach(() => {
  vi.unstubAllEnvs();
  window.history.pushState({}, "", "/");
});

describe("App", () => {
  it("wires every provider and the router: a visitor without sign-in lands on the sign-in page", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/sign-in");
    expect(screen.getByRole("alert")).toHaveTextContent("VITE_SUPABASE_URL");
  });
});
