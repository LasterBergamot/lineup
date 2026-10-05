import { afterEach } from "vitest";
import { createApi } from "@/api/client";
import { ApiError } from "@/api/errors";
import { generateLineup } from "@/features/lineup/generate";

afterEach(() => vi.unstubAllGlobals());

const body = {
  match: "M",
  division: "D",
  team_name: "T",
  cap: "Kék" as const,
  date: "2024",
  coach: "a",
  doctor: "b",
  assistant_coach: "c",
  team_leader: "d",
  ball_thrower: "e",
  players: [{ cap_number: 1, name: "P", nssz_number: "N" }],
};

const client = createApi("http://localhost/api");

describe("generateLineup", () => {
  it("posts the body with the chosen format and returns the file and its name", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response("%PDF-", {
          headers: {
            "content-disposition": `attachment; filename="x.pdf"; filename*=UTF-8''r%C3%A1jt.pdf`,
          },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const file = await generateLineup(body, "pdf", client);

    const sent = (fetchMock.mock.calls[0] as unknown as [Request])[0];
    expect(sent.method).toBe("POST");
    expect(sent.url).toBe("http://localhost/api/lineups?format=pdf");
    expect(await sent.json()).toEqual(body);
    expect(file.filename).toBe("rájt.pdf");
    expect(await file.blob.text()).toBe("%PDF-");
  });

  it("falls back to a default name when the header is missing", async () => {
    vi.stubGlobal("fetch", async () => new Response("x"));
    expect((await generateLineup(body, "docx", client)).filename).toBe("lineup.docx");
  });

  it("surfaces the per-field messages of a 422 as an ApiError", async () => {
    const detail = [{ loc: ["body", "match"], msg: "String should have at most 200 characters" }];
    vi.stubGlobal("fetch", async () => Response.json({ detail }, { status: 422 }));
    await expect(generateLineup(body, "pdf", client)).rejects.toMatchObject({
      status: 422,
      body: { detail },
    });
  });

  it("reports a dropped connection as status 0", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("Failed to fetch")));
    const error = await generateLineup(body, "pdf", client).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
  });
});
