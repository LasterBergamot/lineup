import { ApiError } from "@/api/errors";
import { createQueryClient, MAX_RETRIES, retryDelay, shouldRetry } from "@/api/query-client";

describe("shouldRetry", () => {
  it("retries transient failures up to the limit", () => {
    expect(shouldRetry(0, new ApiError(503))).toBe(true);
    expect(shouldRetry(MAX_RETRIES - 1, new ApiError(0))).toBe(true);
    expect(shouldRetry(MAX_RETRIES, new ApiError(503))).toBe(false);
  });

  it("never retries a 4xx answer", () => {
    expect(shouldRetry(0, new ApiError(404))).toBe(false);
    expect(shouldRetry(0, new ApiError(422))).toBe(false);
  });
});

describe("retryDelay", () => {
  it("backs off 1 s, 2 s, 4 s and then settles at 8 s", () => {
    expect([0, 1, 2, 3, 4, 10].map(retryDelay)).toEqual([1000, 2000, 4000, 8000, 8000, 8000]);
  });

  it("keeps the whole retry budget near a minute", () => {
    const total = Array.from({ length: MAX_RETRIES }, (_, i) => retryDelay(i)).reduce(
      (a, b) => a + b,
    );
    expect(total).toBeGreaterThan(40_000);
    expect(total).toBeLessThanOrEqual(60_000);
  });
});

describe("createQueryClient", () => {
  it("retries queries with the shared policy but never retries mutations", () => {
    const defaults = createQueryClient().getDefaultOptions();
    expect(defaults.queries?.retry).toBe(shouldRetry);
    expect(defaults.queries?.retryDelay).toBe(retryDelay);
    expect(defaults.mutations?.retry).toBe(false);
  });
});
