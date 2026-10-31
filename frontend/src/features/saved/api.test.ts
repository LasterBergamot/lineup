import { createApi } from "@/api/client";
import {
  deleteSavedLineup,
  listSavedLineups,
  savedLineupsKey,
  savedPreviewKey,
  type SavedLineup,
} from "@/features/saved/api";

afterEach(() => vi.unstubAllGlobals());

/** Answers each request with the next response in turn and records what was sent. */
function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn(async () => responses.shift()!);
  vi.stubGlobal("fetch", fetchMock);
  const sent = (index: number) => (fetchMock.mock.calls[index] as unknown as [Request])[0];
  return {
    count: () => fetchMock.mock.calls.length,
    url: (index = 0) => sent(index).url,
    method: (index = 0) => sent(index).method,
  };
}

const client = () => createApi("http://localhost/api");
const TEAM = "00000000-0000-4000-8000-000000000001";

const lineup = (n: number) => ({ id: `l-${n}`, match_name: `Match ${n}` }) as SavedLineup;
const page = (items: SavedLineup[], total: number) =>
  Response.json({ items, total, limit: 200, offset: 0 });

describe("saved lineup keys", () => {
  it("start with the prefix the creator invalidates after saving", () => {
    expect(savedLineupsKey("u", TEAM)).toEqual(["saved", "u", TEAM]);
    expect(savedPreviewKey("u", TEAM, "l-1")).toEqual(["saved", "u", TEAM, "preview", "l-1"]);
  });
});

describe("listSavedLineups", () => {
  it("reads every page of the team's lineups and lists the newest first", async () => {
    const fetchMock = stubFetch(page([lineup(1), lineup(2)], 3), page([lineup(3)], 3));
    const result = await listSavedLineups(TEAM, client());
    expect(result.map((l) => l.id)).toEqual(["l-3", "l-2", "l-1"]);
    expect(fetchMock.url(0)).toBe(
      `http://localhost/api/lineups/saved?team_id=${TEAM}&limit=200&offset=0`,
    );
    expect(fetchMock.url(1)).toContain("offset=2");
  });

  it("stops at an empty page when lineups were deleted meanwhile", async () => {
    const fetchMock = stubFetch(page([lineup(1)], 5), page([], 5));
    expect(await listSavedLineups(TEAM, client())).toHaveLength(1);
    expect(fetchMock.count()).toBe(2);
  });

  it("throws an ApiError on failure", async () => {
    stubFetch(Response.json({ detail: "Team not found" }, { status: 404 }));
    await expect(listSavedLineups(TEAM, client())).rejects.toMatchObject({ status: 404 });
  });
});

describe("deleteSavedLineup", () => {
  it("deletes the lineup by id", async () => {
    const fetchMock = stubFetch(new Response(null, { status: 204 }));
    await deleteSavedLineup("l-1", client());
    expect(fetchMock.method()).toBe("DELETE");
    expect(fetchMock.url()).toBe("http://localhost/api/lineups/saved/l-1");
  });

  it("reports a lineup that is already gone as a 404", async () => {
    stubFetch(Response.json({ detail: "Not found" }, { status: 404 }));
    await expect(deleteSavedLineup("l-1", client())).rejects.toMatchObject({ status: 404 });
  });
});
