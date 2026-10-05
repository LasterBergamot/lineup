import type { Middleware } from "openapi-fetch";
import { createApi } from "@/api/client";
import { createAuthMiddleware } from "@/api/auth-middleware";

afterEach(() => vi.unstubAllGlobals());

/** Runs one call through a client that uses the middleware; returns the request the server saw. */
async function call(middleware: Middleware, status = 200) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status }));
  vi.stubGlobal("fetch", fetchMock);
  await createApi("http://localhost/api", 1000, middleware).GET("/teams", {});
  return (fetchMock.mock.calls[0] as unknown as [Request])[0];
}

describe("createAuthMiddleware", () => {
  it("sends the token as a bearer header", async () => {
    const request = await call(createAuthMiddleware(async () => "the-token", vi.fn()));
    expect(request.headers.get("Authorization")).toBe("Bearer the-token");
  });

  it("sends no header when nobody is signed in", async () => {
    const request = await call(createAuthMiddleware(async () => null, vi.fn()));
    expect(request.headers.has("Authorization")).toBe(false);
  });

  it("leaves the health probe alone, without even asking for a token", async () => {
    const getToken = vi.fn(async () => "the-token");
    const fetchMock = vi.fn(async () => Response.json({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);
    await createApi("http://localhost/api", 1000, createAuthMiddleware(getToken, vi.fn())).GET(
      "/health",
      {},
    );
    const request = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(request.headers.has("Authorization")).toBe(false);
    expect(getToken).not.toHaveBeenCalled();
  });

  it("reports a 401 to a call that carried a token", async () => {
    const onUnauthorized = vi.fn();
    await call(
      createAuthMiddleware(async () => "the-token", onUnauthorized),
      401,
    );
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("ignores a 401 to a call without a token, and other failures", async () => {
    const onUnauthorized = vi.fn();
    await call(
      createAuthMiddleware(async () => null, onUnauthorized),
      401,
    );
    await call(
      createAuthMiddleware(async () => "the-token", onUnauthorized),
      503,
    );
    await call(
      createAuthMiddleware(async () => "the-token", onUnauthorized),
      403,
    );
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
