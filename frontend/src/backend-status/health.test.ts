import { afterEach } from "vitest";
import { createApi } from "@/api/client";
import {
  createProbe,
  GIVE_UP_AFTER_MS,
  RETRY_DELAYS_MS,
  waitForBackend,
  type Probe,
  type ProbeResult,
} from "@/backend-status/health";

afterEach(() => vi.unstubAllGlobals());

describe("createProbe", () => {
  const probe = createProbe(createApi("http://localhost/api"));
  const signal = new AbortController().signal;

  function serverAnswers(status: number) {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "x" }), { status }));
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("calls /health for liveness and /health?db=true for readiness", async () => {
    const fetchMock = serverAnswers(200);
    await probe(false, signal);
    await probe(true, signal);
    const urls = fetchMock.mock.calls.map((call) => (call as unknown as [Request])[0].url);
    expect(urls).toEqual(["http://localhost/api/health", "http://localhost/api/health?db=true"]);
  });

  it("maps 200 to ok", async () => {
    serverAnswers(200);
    expect(await probe(false, signal)).toBe("ok");
  });

  it("maps a 503 from the readiness check to unavailable (database down)", async () => {
    serverAnswers(503);
    expect(await probe(true, signal)).toBe("unavailable");
  });

  it.each([502, 503, 504])("treats %i on the liveness check as transient", async (status) => {
    serverAnswers(status);
    expect(await probe(false, signal)).toBe("transient");
  });

  it("treats other statuses as fatal", async () => {
    serverAnswers(404);
    expect(await probe(false, signal)).toBe("fatal");
  });

  it("treats a network failure as transient", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("Failed to fetch")));
    expect(await probe(false, signal)).toBe("transient");
  });
});

describe("waitForBackend", () => {
  function scripted(results: ProbeResult[]): Probe {
    const queue = [...results];
    return async () => queue.shift() ?? "transient";
  }

  it("returns ready on the first answer without sleeping", async () => {
    const sleep = vi.fn(async () => {});
    const result = await waitForBackend({
      signal: new AbortController().signal,
      probe: scripted(["ok"]),
      sleep,
    });
    expect(result).toBe("ready");
    expect(sleep).not.toHaveBeenCalled();
  });

  it("retries transient failures with growing pauses until the backend answers", async () => {
    const sleep = vi.fn<(ms: number) => Promise<void>>(async () => {});
    const result = await waitForBackend({
      signal: new AbortController().signal,
      probe: scripted(["transient", "transient", "transient", "transient", "transient", "ok"]),
      sleep,
    });
    expect(result).toBe("ready");
    expect(sleep.mock.calls.map(([ms]) => ms)).toEqual([
      ...RETRY_DELAYS_MS,
      RETRY_DELAYS_MS.at(-1),
    ]);
  });

  it("does not retry a non-retryable answer", async () => {
    const sleep = vi.fn(async () => {});
    const result = await waitForBackend({
      signal: new AbortController().signal,
      probe: scripted(["fatal"]),
      sleep,
    });
    expect(result).toBe("down");
    expect(sleep).not.toHaveBeenCalled();
  });

  it("gives up after the time budget", async () => {
    let clock = 0;
    const result = await waitForBackend({
      signal: new AbortController().signal,
      probe: async () => "transient",
      sleep: async (ms) => {
        clock += ms * 20;
      },
      now: () => clock,
    });
    expect(result).toBe("down");
    expect(clock).toBeGreaterThanOrEqual(GIVE_UP_AFTER_MS);
  });

  it("stops as soon as the signal aborts", async () => {
    const controller = new AbortController();
    const probe: Probe = async () => {
      controller.abort();
      return "transient";
    };
    const sleep = vi.fn(async () => {});
    expect(await waitForBackend({ signal: controller.signal, probe, sleep })).toBe("down");
    expect(sleep).not.toHaveBeenCalled();
  });

  it("sleeps for real, and wakes early on abort, with the default sleep", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const probe = vi.fn<Probe>(async () => "transient");
    const waiting = waitForBackend({ signal: controller.signal, probe });
    await vi.advanceTimersByTimeAsync(0);
    expect(probe).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(RETRY_DELAYS_MS[0]!);
    expect(probe).toHaveBeenCalledTimes(2);
    controller.abort();
    expect(await waiting).toBe("down");
    vi.useRealTimers();
  });
});
