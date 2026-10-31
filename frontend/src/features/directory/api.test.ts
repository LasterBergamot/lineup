import { createApi } from "@/api/client";
import { ApiError } from "@/api/errors";
import { poolKey, searchPool } from "@/features/directory/api";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response) {
  const fetchMock = vi.fn(async () => response);
  vi.stubGlobal("fetch", fetchMock);
  return () => new URL((fetchMock.mock.calls[0] as unknown as [Request])[0].url);
}

const client = () => createApi("http://localhost/api");
const TEAMS = [
  { id: "00000000-0000-4000-8000-000000000001", name: "BVSC" },
  { id: "00000000-0000-4000-8000-000000000002", name: "FTC" },
];

describe("directory api", () => {
  it("sends the search term and the limit", async () => {
    const seen = stubFetch(Response.json(TEAMS));
    await expect(searchPool("Fradi", 20, client())).resolves.toEqual(TEAMS);
    const url = seen();
    expect(url.pathname).toBe("/api/teams/pool");
    expect(url.searchParams.get("search")).toBe("Fradi");
    expect(url.searchParams.get("limit")).toBe("20");
  });

  it("trims the term", async () => {
    const seen = stubFetch(Response.json([]));
    await searchPool("  Fradi ", 20, client());
    expect(seen().searchParams.get("search")).toBe("Fradi");
  });

  it("leaves the search out when it is blank", async () => {
    const seen = stubFetch(Response.json(TEAMS));
    await searchPool("   ", 20, client());
    const url = seen();
    expect(url.searchParams.has("search")).toBe(false);
    expect(url.searchParams.get("limit")).toBe("20");
  });

  it("throws an ApiError on failure", async () => {
    stubFetch(Response.json({ detail: "nope" }, { status: 503 }));
    const failure = searchPool("", 20, client());
    await expect(failure).rejects.toBeInstanceOf(ApiError);
    await expect(failure).rejects.toHaveProperty("status", 503);
  });

  it("keys the cache by user and search", () => {
    expect(poolKey("a", "x")).not.toEqual(poolKey("b", "x"));
    expect(poolKey("a", "x")).not.toEqual(poolKey("a", "y"));
  });
});
