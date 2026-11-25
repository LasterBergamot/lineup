import { createApi } from "@/api/client";
import {
  deleteSavedLineup,
  hasFilters,
  listSavedLineups,
  NO_FILTERS,
  PAGE_SIZE,
  savedLineupsKey,
  savedListKey,
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
    expect(savedPreviewKey("u", TEAM, "l-1", "v1")).toEqual([
      "saved",
      "u",
      TEAM,
      "preview",
      "l-1",
      "v1",
    ]);
    expect(savedListKey("u", TEAM, NO_FILTERS)).toEqual(["saved", "u", TEAM, "list", NO_FILTERS]);
  });

  it("give each version of a lineup its own preview key, so an edit never shows the old file", () => {
    expect(savedPreviewKey("u", TEAM, "l-1", "v1")).not.toEqual(
      savedPreviewKey("u", TEAM, "l-1", "v2"),
    );
  });
});

describe("listSavedLineups", () => {
  it("asks for one page of the team's lineups and reports where it started", async () => {
    const fetchMock = stubFetch(page([lineup(3), lineup(2)], 3));
    const result = await listSavedLineups(TEAM, NO_FILTERS, 0, client());
    expect(result).toEqual({ items: [lineup(3), lineup(2)], total: 3, offset: 0 });
    expect(fetchMock.url()).toBe(
      `http://localhost/api/lineups/saved?team_id=${TEAM}&limit=${PAGE_SIZE}&offset=0`,
    );
  });

  it("starts the next page at the given offset", async () => {
    const fetchMock = stubFetch(page([lineup(1)], 3));
    const result = await listSavedLineups(TEAM, NO_FILTERS, 2, client());
    expect(result.offset).toBe(2);
    expect(fetchMock.url()).toContain("offset=2");
  });

  it("sends every filter that is set, trimmed, and leaves blank ones out", async () => {
    const fetchMock = stubFetch(page([], 0), page([], 0));
    await listSavedLineups(
      TEAM,
      {
        opponent: "  Csongrád ",
        dateFrom: "2026-10-01",
        dateTo: "2026-10-31",
        location: " Szeged",
      },
      0,
      client(),
    );
    const sent = new URL(fetchMock.url(0)).searchParams;
    expect(Object.fromEntries(sent)).toMatchObject({
      opponent: "Csongrád",
      date_from: "2026-10-01",
      date_to: "2026-10-31",
      location: "Szeged",
    });
    await listSavedLineups(TEAM, { ...NO_FILTERS, opponent: "   ", location: " " }, 0, client());
    const blank = new URL(fetchMock.url(1)).searchParams;
    expect([...blank.keys()].sort()).toEqual(["limit", "offset", "team_id"]);
  });

  it("throws an ApiError on failure", async () => {
    stubFetch(Response.json({ detail: "Team not found" }, { status: 404 }));
    await expect(listSavedLineups(TEAM, NO_FILTERS, 0, client())).rejects.toMatchObject({
      status: 404,
    });
  });
});

describe("hasFilters", () => {
  it("is false for nothing or blanks, true as soon as one filter has content", () => {
    expect(hasFilters(NO_FILTERS)).toBe(false);
    expect(hasFilters({ ...NO_FILTERS, opponent: "  " })).toBe(false);
    expect(hasFilters({ ...NO_FILTERS, dateTo: "2026-10-01" })).toBe(true);
    expect(hasFilters({ ...NO_FILTERS, location: "x" })).toBe(true);
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
