import { createApi } from "@/api/client";
import { ApiError } from "@/api/errors";
import {
  createStaff,
  deleteStaff,
  listStaff,
  staffDefaults,
  staffKey,
  staffOfRole,
  staffSuggestions,
  updateStaff,
  type Staff,
} from "@/features/staff/api";

afterEach(() => vi.unstubAllGlobals());

/** Answers each request with the next response in turn; `seen(i)` reads the i-th request. */
function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn(async () => responses.shift()!);
  vi.stubGlobal("fetch", fetchMock);
  return async (index = 0) => {
    const request = (fetchMock.mock.calls[index] as unknown as [Request])[0];
    return { request, body: await request.clone().text() };
  };
}

const client = () => createApi("http://localhost/api");
const TEAM = "00000000-0000-4000-8000-000000000001";
const ENTRY = "66666666-6666-4666-8666-666666666666";
const PLAYER = "44444444-4444-4444-8444-444444444444";

function staff(name: string, role: Staff["role"], is_default = false): Staff {
  return {
    id: `st-${name}`,
    team_id: TEAM,
    role,
    name,
    source_player_id: null,
    is_default,
    created_at: "2026-11-01T10:00:00",
  };
}

describe("staff api", () => {
  it("keys the cache by user and team only", () => {
    expect(staffKey("u-1", TEAM)).toEqual(["staff", "u-1", TEAM]);
  });

  it("lists a team's staff", async () => {
    const seen = stubFetch(Response.json([staff("Edző Ede", "coach")]));
    expect((await listStaff(TEAM, client())).map((s) => s.name)).toEqual(["Edző Ede"]);
    expect((await seen()).request.url).toBe(`http://localhost/api/teams/${TEAM}/staff`);
  });

  it("creates a typed-in entry without a source player", async () => {
    const seen = stubFetch(Response.json(staff("Edző Ede", "coach"), { status: 201 }));
    await createStaff(
      TEAM,
      { role: "coach", name: "Edző Ede", playerId: "", isDefault: true },
      client(),
    );
    const { request, body } = await seen();
    expect(request.method).toBe("POST");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/staff`);
    expect(JSON.parse(body)).toEqual({
      role: "coach",
      name: "Edző Ede",
      is_default: true,
      source_player_id: null,
    });
  });

  it("replaces every field of an entry, the picked player included", async () => {
    const seen = stubFetch(Response.json(staff("Kovács Béla", "team_leader")));
    await updateStaff(
      { id: ENTRY, team_id: TEAM },
      { role: "team_leader", name: "Kovács Béla", playerId: PLAYER, isDefault: false },
      client(),
    );
    const { request, body } = await seen();
    expect(request.method).toBe("PUT");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/staff/${ENTRY}`);
    expect(JSON.parse(body)).toEqual({
      role: "team_leader",
      name: "Kovács Béla",
      is_default: false,
      source_player_id: PLAYER,
    });
  });

  it("deletes an entry and reports a failure as ApiError", async () => {
    const seen = stubFetch(
      new Response(null, { status: 204 }),
      new Response(null, { status: 404 }),
    );
    await deleteStaff({ id: ENTRY, team_id: TEAM }, client());
    const { request } = await seen();
    expect(request.method).toBe("DELETE");
    expect(request.url).toBe(`http://localhost/api/teams/${TEAM}/staff/${ENTRY}`);
    await expect(deleteStaff({ id: ENTRY, team_id: TEAM }, client())).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});

describe("staff helpers", () => {
  const all = [
    staff("Zsigmond Zoltán", "coach"),
    staff("Csonka Csaba", "coach"),
    staff("Szabó Ödön", "coach", true),
    staff("Csonka Csaba", "coach"),
    staff("Dobó Dóra", "ball_thrower", true),
    staff("Segéd Sára", "assistant_coach"),
  ];

  it("orders a role's entries default first, then in Hungarian alphabetical order", () => {
    expect(staffOfRole(all, "coach").map((s) => s.name)).toEqual([
      "Szabó Ödön",
      "Csonka Csaba",
      "Csonka Csaba",
      "Zsigmond Zoltán",
    ]);
    expect(staffOfRole(all, "team_leader")).toEqual([]);
  });

  it("suggests each name of a role once, in that order", () => {
    expect(staffSuggestions(all, "coach")).toEqual([
      { value: "Szabó Ödön", label: "Szabó Ödön" },
      { value: "Csonka Csaba", label: "Csonka Csaba" },
      { value: "Zsigmond Zoltán", label: "Zsigmond Zoltán" },
    ]);
  });

  it("reads each role's default, empty where a role has none", () => {
    expect(staffDefaults(all)).toEqual({
      coach: "Szabó Ödön",
      assistant_coach: "",
      team_leader: "",
      ball_thrower: "Dobó Dóra",
    });
    expect(staffDefaults([])).toEqual({
      coach: "",
      assistant_coach: "",
      team_leader: "",
      ball_thrower: "",
    });
  });
});
