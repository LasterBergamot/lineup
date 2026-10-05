import { ApiError, describeError, isTransient, request } from "@/api/errors";

const ok = (data: unknown) =>
  Promise.resolve({ data, response: new Response(null, { status: 200 }) });

describe("isTransient", () => {
  it.each([0, 502, 503, 504])("retries status %i", (status) => {
    expect(isTransient(new ApiError(status))).toBe(true);
  });

  it.each([400, 404, 409, 422, 500])("does not retry status %i", (status) => {
    expect(isTransient(new ApiError(status))).toBe(false);
  });

  it("does not retry things that are not API errors", () => {
    expect(isTransient(new Error("boom"))).toBe(false);
  });
});

describe("request", () => {
  it("returns the data of a successful call", async () => {
    await expect(request(ok({ status: "ok" }))).resolves.toEqual({ status: "ok" });
  });

  it("throws an ApiError with the status and body when the server answers with an error", async () => {
    const call = Promise.resolve({
      error: { detail: "nope" },
      response: new Response(null, { status: 409 }),
    });
    await expect(request(call)).rejects.toMatchObject({ status: 409, body: { detail: "nope" } });
  });

  it("throws an ApiError even when only the status says it failed", async () => {
    const call = Promise.resolve({ response: new Response(null, { status: 500 }) });
    await expect(request(call)).rejects.toMatchObject({ status: 500 });
  });

  it("maps a rejected fetch (no response at all) to status 0", async () => {
    await expect(request(Promise.reject(new TypeError("Failed to fetch")))).rejects.toMatchObject({
      status: 0,
    });
  });
});

describe("describeError", () => {
  it.each([
    [0, /can't reach the server/i],
    [422, /rejected/i],
    [502, /busy or starting up/i],
    [503, /busy or starting up/i],
    [504, /too long/i],
    [500, /went wrong on our side/i],
  ])("explains status %i", (status, message) => {
    expect(describeError(new ApiError(status))).toMatch(message);
  });

  it("stays generic for unknown errors and never echoes server text", () => {
    expect(describeError(new Error("secret detail"))).toBe(
      "Something went wrong. Please try again.",
    );
    expect(describeError(new ApiError(500, { detail: "secret detail" }))).not.toMatch(/secret/);
  });
});
