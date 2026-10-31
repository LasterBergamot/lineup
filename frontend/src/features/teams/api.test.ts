import { ApiError } from "@/api/errors";
import { createApi } from "@/api/client";
import { createTeam, listTeams, teamsKey, updateTeam } from "@/features/teams/api";
import { teamsPage } from "@/test/auth";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(response: Response) {
  const fetchMock = vi.fn(async () => response);
  vi.stubGlobal("fetch", fetchMock);
  return async () => {
    const request = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    return { request, body: await request.clone().text() };
  };
}

const client = () => createApi("http://localhost/api");

describe("teams api", () => {
  it("lists the caller's teams in one request", async () => {
    const seen = stubFetch(Response.json(teamsPage("A", "B")));
    const teams = await listTeams(client());
    expect(teams.map((t) => t.name)).toEqual(["A", "B"]);
    expect((await seen()).request.url).toBe("http://localhost/api/teams?limit=200");
  });

  it("creates a team, sending the listing choice as is_public", async () => {
    const seen = stubFetch(Response.json(teamsPage("New").items[0], { status: 201 }));
    const team = await createTeam({ name: "New", isPublic: false }, client());
    expect(team.name).toBe("New");
    const { request, body } = await seen();
    expect(request.method).toBe("POST");
    expect(JSON.parse(body)).toEqual({ name: "New", is_public: false });
  });

  it("updates a team with PUT, sending both the name and the listing choice", async () => {
    const updated = { ...teamsPage("Renamed").items[0], is_public: false };
    const seen = stubFetch(Response.json(updated));
    const team = await updateTeam(
      "00000000-0000-4000-8000-000000000001",
      { name: "Renamed", isPublic: false },
      client(),
    );
    expect(team).toEqual(updated);
    const { request, body } = await seen();
    expect(request.method).toBe("PUT");
    expect(request.url).toBe("http://localhost/api/teams/00000000-0000-4000-8000-000000000001");
    expect(JSON.parse(body)).toEqual({ name: "Renamed", is_public: false });
  });

  it("reports a refused update as an ApiError with its status", async () => {
    stubFetch(Response.json({ detail: "Only the owner can do that" }, { status: 403 }));
    await expect(updateTeam("t", { name: "X", isPublic: true }, client())).rejects.toMatchObject({
      status: 403,
    });
  });

  it("turns a failure into an ApiError", async () => {
    stubFetch(Response.json({ detail: "Not authenticated" }, { status: 401 }));
    await expect(listTeams(client())).rejects.toMatchObject({ status: 401 });
    await expect(listTeams(client())).rejects.toBeInstanceOf(ApiError);
  });

  it("keys the cache by user, so two people never share cached teams", () => {
    expect(teamsKey("a")).not.toEqual(teamsKey("b"));
    expect(teamsKey(null)).toEqual(["teams", null]);
  });
});
