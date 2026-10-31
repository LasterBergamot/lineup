import { afterEach } from "vitest";
import { createApi } from "@/api/client";
import { listRecentOpponents, recentOpponentsKey } from "@/features/creator/opponent/api";

afterEach(() => vi.unstubAllGlobals());

const client = createApi("http://localhost/api");

describe("listRecentOpponents", () => {
  it("asks the team's recent-opponents endpoint with the limit", async () => {
    const fetchMock = vi.fn(async () => Response.json(["FTC", "Szeged"]));
    vi.stubGlobal("fetch", fetchMock);

    expect(await listRecentOpponents("team-1", 5, client)).toEqual(["FTC", "Szeged"]);

    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.method).toBe("GET");
    expect(sent.url).toBe("http://localhost/api/teams/team-1/opponents/recent?limit=5");
  });

  it("asks for 20 names by default", async () => {
    const fetchMock = vi.fn(async () => Response.json([]));
    vi.stubGlobal("fetch", fetchMock);
    await listRecentOpponents("team-1", undefined, client);
    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.url).toBe("http://localhost/api/teams/team-1/opponents/recent?limit=20");
  });

  it("throws an ApiError for a team the caller is not in", async () => {
    vi.stubGlobal("fetch", async () => Response.json({ detail: "x" }, { status: 404 }));
    await expect(listRecentOpponents("team-1", 20, client)).rejects.toMatchObject({
      status: 404,
    });
  });
});

describe("recentOpponentsKey", () => {
  it("holds ids only, the user first so people never share a cache entry", () => {
    expect(recentOpponentsKey("user-1", "team-1")).toEqual([
      "recent-opponents",
      "user-1",
      "team-1",
    ]);
  });
});
