import { createApi } from "@/api/client";
import { createSavedLineup } from "@/features/creator/api";

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
