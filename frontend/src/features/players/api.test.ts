import { createApi } from "@/api/client";
import {
  createPlayer,
  deletePlayer,
  listPlayers,
  playersKey,
  updatePlayer,
  type Player,
} from "@/features/players/api";

afterEach(() => vi.unstubAllGlobals());

/** Answers each request with the next response in turn; `seen(i)` reads the i-th request. */
function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn(async () => responses.shift()!);
  vi.stubGlobal("fetch", fetchMock);
  return {
    count: () => fetchMock.mock.calls.length,
    seen: async (index = 0) => {
      const request = (fetchMock.mock.calls[index] as unknown as [Request])[0];
      return { request, body: await request.clone().text() };
    },
  };
}

const client = () => createApi("http://localhost/api");
const TEAM = "00000000-0000-4000-8000-000000000001";
const PLAYER = "44444444-4444-4444-8444-444444444444";

function player(n: number): Player {
  return {
    id: `p-${n}`,
    team_id: TEAM,
    name: `Player ${n}`,
    nssz_number: `N${n}`,
    created_at: "2026-10-05T10:00:00",
  };
}

function page(items: Player[], total: number, offset = 0) {
  return Response.json({ items, total, limit: 200, offset });
}

describe("players api", () => {
  it("lists one team's roster in a single request when it fits in a page", async () => {
    const fetch = stubFetch(page([player(1), player(2)], 2));
    const players = await listPlayers(TEAM, client());
    expect(players.map((p) => p.name)).toEqual(["Player 1", "Player 2"]);
    expect(fetch.count()).toBe(1);
    expect((await fetch.seen()).request.url).toBe(
      `http://localhost/api/players?team_id=${TEAM}&limit=200&offset=0`,
    );
  });

  it("reads every page of a roster longer than the API's cap, in order", async () => {
    const first = Array.from({ length: 200 }, (_, i) => player(i));
    const fetch = stubFetch(page(first, 201), page([player(200)], 201, 200));
    const players = await listPlayers(TEAM, client());
    expect(players).toHaveLength(201);
    expect(players.at(-1)!.name).toBe("Player 200");
    expect(fetch.count()).toBe(2);
    expect((await fetch.seen(1)).request.url).toContain("offset=200");
  });

  it("stops at an empty page even if the total said there were more", async () => {
    const fetch = stubFetch(page([player(1)], 3), page([], 1, 1));
    expect(await listPlayers(TEAM, client())).toHaveLength(1);
    expect(fetch.count()).toBe(2);
  });

  it("returns an empty roster", async () => {
    stubFetch(page([], 0));
    expect(await listPlayers(TEAM, client())).toEqual([]);
  });

  it("throws ApiError when the list fails", async () => {
    stubFetch(Response.json({ detail: "x" }, { status: 500 }));
    await expect(listPlayers(TEAM, client())).rejects.toMatchObject({ status: 500 });
  });

  it("creates a player on the given team", async () => {
    const fetch = stubFetch(Response.json(player(1), { status: 201 }));
    const created = await createPlayer(TEAM, { name: "Player 1", nsszNumber: "N1" }, client());
    expect(created.id).toBe("p-1");
    const { request, body } = await fetch.seen();
    expect(request.method).toBe("POST");
    expect(request.url).toBe("http://localhost/api/players");
    expect(JSON.parse(body)).toEqual({ team_id: TEAM, name: "Player 1", nssz_number: "N1" });
  });

  it("updates a player, sending its team back so it stays on the roster", async () => {
    const fetch = stubFetch(Response.json(player(1)));
    await updatePlayer({ id: PLAYER, team_id: TEAM }, { name: "New", nsszNumber: "N9" }, client());
    const { request, body } = await fetch.seen();
    expect(request.method).toBe("PUT");
    expect(request.url).toBe(`http://localhost/api/players/${PLAYER}`);
    expect(JSON.parse(body)).toEqual({ team_id: TEAM, name: "New", nssz_number: "N9" });
  });

  it("deletes a player", async () => {
    const fetch = stubFetch(new Response(null, { status: 204 }));
    await expect(deletePlayer(PLAYER, client())).resolves.toBeUndefined();
    const { request } = await fetch.seen();
    expect(request.method).toBe("DELETE");
    expect(request.url).toBe(`http://localhost/api/players/${PLAYER}`);
  });

  it("keys the cache by user and team, with ids only", () => {
    expect(playersKey("a", TEAM)).toEqual(["players", "a", TEAM]);
    expect(playersKey("a", TEAM)).not.toEqual(playersKey("b", TEAM));
  });
});
