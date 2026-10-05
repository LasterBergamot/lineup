import {
  ApiError,
  describeError,
  fieldErrors,
  isTransient,
  request,
  requestWithResponse,
} from "@/api/errors";

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

describe("requestWithResponse", () => {
  it("returns the data together with the response, so callers can read headers", async () => {
    const response = new Response(null, { status: 200, headers: { "x-test": "1" } });
    const result = await requestWithResponse(Promise.resolve({ data: "body", response }));
    expect(result.data).toBe("body");
    expect(result.response.headers.get("x-test")).toBe("1");
  });
});

describe("fieldErrors", () => {
  it("turns a FastAPI 422 body into dotted field paths and plain messages", () => {
    const error = new ApiError(422, {
      detail: [
        { loc: ["body", "match"], msg: "Field required" },
        {
          loc: ["body", "players", 2, "name"],
          msg: "Value error, must not contain control characters",
        },
      ],
    });
    expect(fieldErrors(error)).toEqual([
      { path: "match", message: "Field required" },
      { path: "players.2.name", message: "must not contain control characters" },
    ]);
  });

  it("skips entries that do not point at a body field or are malformed", () => {
    const error = new ApiError(422, {
      detail: [
        { loc: ["query", "format"], msg: "nope" },
        { loc: ["body"], msg: "whole body" },
        { loc: "body", msg: "not an array" },
        { loc: ["body", "x"], msg: 5 },
      ],
    });
    expect(fieldErrors(error)).toEqual([]);
  });

  it("returns nothing for other statuses, bodies and errors", () => {
    expect(fieldErrors(new ApiError(500, { detail: [{ loc: ["body", "a"], msg: "x" }] }))).toEqual(
      [],
    );
    expect(fieldErrors(new ApiError(422, { detail: "text" }))).toEqual([]);
    expect(fieldErrors(new ApiError(422))).toEqual([]);
    expect(fieldErrors(new Error("x"))).toEqual([]);
  });
});
