import { createApi } from "@/api/client";
import { listMembers, membersKey, removeMember, transferOwnership } from "@/features/members/api";
import { membersList, teamsPage } from "@/test/auth";

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
const TEAM = "00000000-0000-4000-8000-000000000001";
const OTHER = "22222222-2222-4222-8222-222222222222";

describe("members api", () => {
  it("lists the members", async () => {
    const seen = stubFetch(Response.json(membersList({ id: OTHER })));
    const members = await listMembers(TEAM, client());
    expect(members.map((m) => m.is_you)).toEqual([true, false]);
    expect((await seen()).request.url).toBe(`http://localhost/api/teams/${TEAM}/members`);
  });

  it("removes a member, or leaves when given the caller's own id", async () => {
    const seen = stubFetch(new Response(null, { status: 204 }));
    await expect(removeMember(TEAM, OTHER, client())).resolves.toBeUndefined();
    const { request } = await seen();
    expect(request.method).toBe("DELETE");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/members/${OTHER}`);
  });

  it("hands the team over to a member", async () => {
    const seen = stubFetch(Response.json(teamsPage("SZVTK").items[0]));
    await transferOwnership(TEAM, OTHER, client());
    const { request, body } = await seen();
    expect(request.method).toBe("POST");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/transfer-ownership`);
    expect(JSON.parse(body)).toEqual({ user_id: OTHER });
  });

  it("keys the cache by user and team", () => {
    expect(membersKey("a", TEAM)).not.toEqual(membersKey("b", TEAM));
  });
});
