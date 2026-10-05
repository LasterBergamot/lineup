import { afterEach } from "vitest";
import { API_BASE_URL, createApi, fetchWithTimeout, PDF_TIMEOUT_MS } from "@/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("api client", () => {
  it("defaults to the same-origin /api dev proxy when VITE_API_URL is unset", () => {
    expect(API_BASE_URL).toBe("/api");
  });

  it("sends typed requests to the configured base URL", async () => {
    const fetchMock = vi.fn(async () => Response.json({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    const { data, response } = await createApi("http://localhost/api").GET("/health");
    expect(fetchMock).toHaveBeenCalledOnce();
    const request = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(request.url).toBe("http://localhost/api/health");
    expect(response.ok).toBe(true);
    expect(data).toEqual({ status: "ok" });
  });

  it("keeps the PDF timeout above the backend's 120 s LibreOffice limit", () => {
    expect(PDF_TIMEOUT_MS).toBeGreaterThan(120_000);
  });
});

describe("fetchWithTimeout", () => {
  it("aborts a request that takes longer than the timeout", async () => {
    // Real (short) timer on purpose: AbortSignal.timeout runs on a native timer that fake timers
    // do not control, which made a fake-timer version of this test flaky.
    vi.stubGlobal(
      "fetch",
      (request: Request) =>
        new Promise((_resolve, reject) => {
          request.signal.addEventListener("abort", () => reject(request.signal.reason));
        }),
    );
    await expect(fetchWithTimeout(20)(new Request("http://localhost/slow"))).rejects.toMatchObject({
      name: "TimeoutError",
    });
  });

  it("still honours a signal the caller already set", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      (request: Request) =>
        new Promise((_resolve, reject) => {
          request.signal.addEventListener("abort", () => reject(request.signal.reason));
        }),
    );
    const pending = fetchWithTimeout(60_000)(
      new Request("http://localhost/slow", { signal: controller.signal }),
    );
    controller.abort(new Error("cancelled"));
    await expect(pending).rejects.toThrow("cancelled");
  });
});
