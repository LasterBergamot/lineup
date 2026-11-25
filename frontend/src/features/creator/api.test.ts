import { createApi } from "@/api/client";
import {
  createSavedLineup,
  getSavedLineup,
  SavedLineupGoneError,
  updateSavedLineup,
} from "@/features/creator/api";

afterEach(() => vi.unstubAllGlobals());

const client = createApi("http://localhost/api");
const body = {
  team_id: "t",
  source_team_id: "t",
  opponent_name: "Csongrád",
  division: "OB I.",
  cap: "Kék" as const,
  date: "2026",
  coach: "K",
  players: [{ name: "P", nssz_number: "N", cap_number: 1 }],
};

describe("createSavedLineup", () => {
  it("posts the body to /lineups/saved and returns the saved lineup", async () => {
    const fetchMock = vi.fn(async () => Response.json({ id: "s-1" }, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const saved = await createSavedLineup(body, client);
    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.method).toBe("POST");
    expect(sent.url).toBe("http://localhost/api/lineups/saved");
    expect(await sent.json()).toEqual(body);
    expect(saved).toMatchObject({ id: "s-1" });
  });

  it("throws an ApiError for a team the caller is not in", async () => {
    vi.stubGlobal("fetch", async () =>
      Response.json({ detail: "Team not found" }, { status: 404 }),
    );
    await expect(createSavedLineup(body, client)).rejects.toMatchObject({ status: 404 });
  });
});

describe("getSavedLineup", () => {
  it("reads one saved lineup by id", async () => {
    const fetchMock = vi.fn(async () => Response.json({ id: "s-1" }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await getSavedLineup("s-1", client)).toMatchObject({ id: "s-1" });
    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.method).toBe("GET");
    expect(sent.url).toBe("http://localhost/api/lineups/saved/s-1");
  });

  it("throws an ApiError for a lineup that is gone", async () => {
    vi.stubGlobal("fetch", async () => Response.json({ detail: "nope" }, { status: 404 }));
    await expect(getSavedLineup("x", client)).rejects.toMatchObject({ status: 404 });
  });
});

describe("updateSavedLineup", () => {
  const update = {
    source_team_id: "t",
    opponent_name: "Csongrád",
    division: "OB I.",
    cap: "Kék" as const,
    match_date: "2026-11-24",
    coach: "K",
    players: [{ name: "P", nssz_number: "N", cap_number: 1 }],
    expected_updated_at: "2026-11-24T10:00:00.123456Z",
  };

  it("puts the body to /lineups/saved/{id} and returns the new version", async () => {
    const fetchMock = vi.fn(async () => Response.json({ id: "s-1", updated_at: "later" }));
    vi.stubGlobal("fetch", fetchMock);
    expect(await updateSavedLineup("s-1", update, client)).toMatchObject({ updated_at: "later" });
    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.method).toBe("PUT");
    expect(sent.url).toBe("http://localhost/api/lineups/saved/s-1");
    expect(await sent.json()).toEqual(update);
  });

  it("throws the 409 of a stale version as it is, without asking again", async () => {
    const fetchMock = vi.fn(async () => Response.json({ detail: "changed" }, { status: 409 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(updateSavedLineup("s-1", update, client)).rejects.toMatchObject({ status: 409 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("says the lineup is gone when it no longer exists", async () => {
    vi.stubGlobal("fetch", async () => Response.json({ detail: "nope" }, { status: 404 }));
    const error = await updateSavedLineup("s-1", update, client).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(SavedLineupGoneError);
    expect(error).toMatchObject({ status: 404, name: "SavedLineupGoneError" });
  });

  it("keeps a 404 for a player or opponent when the lineup itself still exists", async () => {
    const fetchMock = vi.fn(async (request: Request) =>
      request.method === "PUT"
        ? Response.json({ detail: "Player x not found" }, { status: 404 })
        : Response.json({ id: "s-1" }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const error = await updateSavedLineup("s-1", update, client).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(SavedLineupGoneError);
    expect(error).toMatchObject({ status: 404 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("keeps the 404 when the check itself fails for another reason", async () => {
    vi.stubGlobal("fetch", async (request: Request) =>
      request.method === "PUT"
        ? Response.json({ detail: "nope" }, { status: 404 })
        : Response.json({ detail: "busy" }, { status: 503 }),
    );
    const error = await updateSavedLineup("s-1", update, client).catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(SavedLineupGoneError);
    expect(error).toMatchObject({ status: 404 });
  });

  it("does not ask again after other failures", async () => {
    vi.stubGlobal("fetch", async () => Response.json({ detail: "bad" }, { status: 422 }));
    await expect(updateSavedLineup("s-1", update, client)).rejects.toMatchObject({ status: 422 });
  });
});
