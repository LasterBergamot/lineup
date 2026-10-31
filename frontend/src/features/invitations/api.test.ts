import { createApi } from "@/api/client";
import { ApiError } from "@/api/errors";
import {
  acceptInvitation,
  createInvitation,
  invitationPreviewKey,
  invitationsKey,
  listInvitations,
  previewInvitation,
  revokeInvitation,
} from "@/features/invitations/api";
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
const TEAM = "00000000-0000-4000-8000-000000000001";

describe("invitations api", () => {
  it("previews a link by its code", async () => {
    const preview = {
      team_name: "SZVTK",
      invited_by_name: "Ann",
      expires_at: "2026-10-31T10:00:00",
    };
    const seen = stubFetch(Response.json(preview));
    await expect(previewInvitation("abc_-9", client())).resolves.toEqual(preview);
    const { request } = await seen();
    expect(request.method).toBe("GET");
    expect(request.url).toBe("http://localhost/api/invitations/abc_-9");
  });

  it("accepts a link and returns the team", async () => {
    const seen = stubFetch(Response.json(teamsPage("SZVTK").items[0]));
    const team = await acceptInvitation("abc", client());
    expect(team.name).toBe("SZVTK");
    const { request } = await seen();
    expect(request.method).toBe("POST");
    expect(request.url).toBe("http://localhost/api/invitations/abc/accept");
  });

  it("creates a link with the chosen lifetime", async () => {
    const created = {
      id: "i1",
      code: "c",
      url: "https://x/join/c",
      role: "member",
      expires_at: "x",
    };
    const seen = stubFetch(Response.json(created, { status: 201 }));
    await expect(createInvitation(TEAM, 72, client())).resolves.toEqual(created);
    const { request, body } = await seen();
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/invitations`);
    expect(JSON.parse(body)).toEqual({ expires_in_hours: 72 });
  });

  it("lists the active links", async () => {
    const seen = stubFetch(
      Response.json([{ id: "i1", role: "member", created_at: "a", expires_at: "b" }]),
    );
    expect(await listInvitations(TEAM, client())).toHaveLength(1);
    expect((await seen()).request.url).toBe(`http://localhost/api/teams/${TEAM}/invitations`);
  });

  it("revokes a link", async () => {
    const seen = stubFetch(new Response(null, { status: 204 }));
    await expect(revokeInvitation(TEAM, "i1", client())).resolves.toBeUndefined();
    const { request } = await seen();
    expect(request.method).toBe("DELETE");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/invitations/i1`);
  });

  it.each([404, 410])("turns a %i into an ApiError with that status", async (status) => {
    stubFetch(Response.json({ detail: "x" }, { status }));
    await expect(previewInvitation("abc", client())).rejects.toBeInstanceOf(ApiError);
    stubFetch(Response.json({ detail: "x" }, { status }));
    await expect(previewInvitation("abc", client())).rejects.toMatchObject({ status });
  });

  it("keys the caches by user and team, and a preview by its code", () => {
    expect(invitationsKey("a", TEAM)).not.toEqual(invitationsKey("b", TEAM));
    expect(invitationPreviewKey("x")).not.toEqual(invitationPreviewKey("y"));
  });
});
