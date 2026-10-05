import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";
import { BackendStatusBanner } from "@/backend-status/banner";
import { useBackendStatus } from "@/backend-status/context";
import type { Probe, ProbeResult } from "@/backend-status/health";
import { BackendStatusProvider, WAKING_AFTER_MS } from "@/backend-status/provider";

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: false }));
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
});

function StatusText() {
  const { status } = useBackendStatus();
  return <p data-testid="status">{status}</p>;
}

/** A probe whose answers the test resolves by hand, so it controls how slow the API is. */
function manualProbe() {
  const pending: { db: boolean; resolve: (r: ProbeResult) => void }[] = [];
  const probe: Probe = (db) => new Promise((resolve) => pending.push({ db, resolve }));
  return { probe, pending };
}

function renderWith(probe: Probe) {
  return render(
    <BackendStatusProvider probe={probe}>
      <StatusText />
      <BackendStatusBanner />
    </BackendStatusProvider>,
  );
}

const status = () => screen.getByTestId("status").textContent;

describe("BackendStatusProvider", () => {
  it("shows nothing for the first moments, then the wake-up banner, then clears it", async () => {
    const { probe, pending } = manualProbe();
    renderWith(probe);
    expect(status()).toBe("unknown");
    expect(screen.queryByRole("status", { name: "" })).not.toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(WAKING_AFTER_MS - 1));
    expect(status()).toBe("unknown");
    expect(screen.queryByText(/starting up/i)).not.toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(status()).toBe("waking");
    expect(screen.getByText(/starting up/i)).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(screen.getByText("(4 s)")).toBeInTheDocument();

    await act(async () => pending[0]!.resolve("ok"));
    expect(status()).toBe("ready");
    expect(screen.queryByText(/starting up/i)).not.toBeInTheDocument();
  });

  it("never shows the banner when the API answers quickly", async () => {
    const probe: Probe = async () => "ok";
    renderWith(probe);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(status()).toBe("ready");
    await act(() => vi.advanceTimersByTimeAsync(WAKING_AFTER_MS * 2));
    expect(screen.queryByText(/starting up/i)).not.toBeInTheDocument();
  });

  it("hides the wake-up banner when VITE_COLD_START_NOTICE is false", async () => {
    vi.stubEnv("VITE_COLD_START_NOTICE", "false");
    const { probe } = manualProbe();
    renderWith(probe);
    await act(() => vi.advanceTimersByTimeAsync(WAKING_AFTER_MS));
    expect(status()).toBe("waking");
    expect(screen.queryByText(/starting up/i)).not.toBeInTheDocument();
  });

  it("reports a paused database once the API is up but the readiness check says 503", async () => {
    const probe: Probe = async (db) => (db ? "unavailable" : "ok");
    renderWith(probe);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(status()).toBe("db-paused");
    expect(screen.getByRole("alert")).toHaveTextContent(/database is paused/i);
  });

  it("stays ready when the readiness check itself fails for another reason", async () => {
    const probe: Probe = async (db) => (db ? "transient" : "ok");
    renderWith(probe);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(status()).toBe("ready");
  });

  it("reports down on a non-retryable answer and can try again", async () => {
    const results: ProbeResult[] = ["fatal", "ok", "ok"];
    const probe = vi.fn<Probe>(async () => results.shift() ?? "ok");
    renderWith(probe);
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(status()).toBe("down");
    expect(screen.getByRole("alert")).toHaveTextContent(/can't reach the server/i);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(status()).toBe("ready");
  });

  it("ignores an answer that arrives after unmount", async () => {
    const { probe, pending } = manualProbe();
    const { unmount } = renderWith(probe);
    unmount();
    await act(async () => pending[0]!.resolve("ok"));
    expect(pending).toHaveLength(1);
  });
});

describe("useBackendStatus", () => {
  it("refuses to work outside the provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<StatusText />)).toThrow(/BackendStatusProvider/);
    spy.mockRestore();
  });
});
