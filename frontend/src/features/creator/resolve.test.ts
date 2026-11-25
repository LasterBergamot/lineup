import type { components } from "@/api/schema";
import {
  emptyValues,
  formPath,
  toLineupRequest,
  toSavedLineupRequest,
  toSavedLineupUpdate,
  valuesForEdit,
  valuesFromSaved,
} from "@/features/creator/resolve";
import type { CreatorValues } from "@/features/creator/schema";
import type { Player } from "@/features/players/api";

type SavedLineup = components["schemas"]["SavedLineupResponse"];

/** The 15 cap rows, with the given ones filled in by cap number. */
function rows(filled: Record<number, Partial<CreatorValues["players"][number]>> = {}) {
  return emptyValues().players.map((row) => ({ ...row, ...filled[row.cap_number] }));
}

const values = (patch: Partial<CreatorValues> = {}): CreatorValues => ({
  ...emptyValues(),
  opponent: "Csongrád",
  division: "OB I.",
  match_date: "2026-11-01",
  coach: "Kovács",
  players: rows({
    1: { playerId: "p-1", name: "Nagy Bence", nssz_number: "N1" },
    4: { name: " Kiss Ádám ", nssz_number: "N4" },
  }),
  ...patch,
});

describe("emptyValues", () => {
  it("starts with white caps and the 15 empty cap rows in cap order", () => {
    const { cap, players } = emptyValues();
    expect(cap).toBe("Fehér");
    expect(players).toHaveLength(15);
    players.forEach((row, index) =>
      expect(row).toEqual({ cap_number: index + 1, playerId: "", name: "", nssz_number: "" }),
    );
  });
});

describe("emptyValues date", () => {
  afterEach(() => vi.useRealTimers());

  it("starts on today's local date with no time", () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 24, 18, 30) });
    expect(emptyValues()).toMatchObject({ match_date: "2026-11-24", match_time: "" });
  });

  it("follows the local midnight, read on each call", () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 24, 23, 59, 59) });
    expect(emptyValues().match_date).toBe("2026-11-24");
    vi.setSystemTime(new Date(2026, 10, 25, 0, 0, 1));
    expect(emptyValues().match_date).toBe("2026-11-25");
  });
});

describe("emptyValues with a team default division", () => {
  it("pre-fills the division and nothing else", () => {
    expect(emptyValues("OB II.")).toEqual({ ...emptyValues(), division: "OB II." });
    expect(emptyValues().division).toBe("");
  });
});

describe("emptyValues with staff defaults", () => {
  it("pre-fills each role that has a default and leaves the doctor empty", () => {
    expect(emptyValues("", { coach: "Edző Ede", team_leader: "Vezető Vera" })).toEqual({
      ...emptyValues(),
      coach: "Edző Ede",
      team_leader: "Vezető Vera",
    });
    expect(emptyValues()).toMatchObject({
      coach: "",
      doctor: "",
      assistant_coach: "",
      team_leader: "",
      ball_thrower: "",
    });
  });
});

describe("toLineupRequest", () => {
  it("names the match after the teams and prints only the filled rows", () => {
    const body = toLineupRequest(values(), "SZVTK");
    expect(body).toMatchObject({
      match: "SZVTK - Csongrád",
      team_name: "SZVTK",
      coach: "Kovács",
      players: [
        { cap_number: 1, name: "Nagy Bence", nssz_number: "N1" },
        { cap_number: 4, name: "Kiss Ádám", nssz_number: "N4" },
      ],
    });
    expect(body.players).toHaveLength(2);
  });

  it("prints the composed date, with the time when one is set", () => {
    expect(toLineupRequest(values(), "SZVTK").date).toBe("2026. 11. 01.");
    expect(toLineupRequest(values({ match_time: "18:30" }), "SZVTK").date).toBe(
      "2026. 11. 01. 18:30",
    );
  });

  it("leaves blank staff out and keeps a given match name", () => {
    const body = toLineupRequest(values({ match_name: "Final", doctor: "Dr. Kis" }), "SZVTK");
    expect(body.match).toBe("Final");
    expect(body.doctor).toBe("Dr. Kis");
    expect(body.assistant_coach).toBeUndefined();
  });

  it("cuts a long default match name to the API's 200 characters", () => {
    const body = toLineupRequest(values({ opponent: "x".repeat(120) }), "y".repeat(120));
    expect(body.match).toHaveLength(200);
  });
});

describe("toSavedLineupRequest", () => {
  it("sends roster players and a listed opponent as ids, and only the filled rows", () => {
    const body = toSavedLineupRequest(values({ opponentId: "opp-1", team_leader: "Vezető" }), {
      id: "team-1",
    });
    expect(body).toMatchObject({
      team_id: "team-1",
      source_team_id: "team-1",
      source_opponent_id: "opp-1",
      team_leader: "Vezető",
      players: [
        { source_player_id: "p-1", cap_number: 1 },
        { name: "Kiss Ádám", nssz_number: "N4", cap_number: 4 },
      ],
    });
    expect(body.players).toHaveLength(2);
    expect(body).not.toHaveProperty("opponent_name");
    expect(body.match_name).toBeUndefined();
    expect(body.doctor).toBeUndefined();
  });

  it("sends the structured date and leaves a blank time out", () => {
    const body = toSavedLineupRequest(values(), { id: "team-1" });
    expect(body).toMatchObject({ match_date: "2026-11-01" });
    expect(body.match_time).toBeUndefined();
    expect(body).not.toHaveProperty("date");
    expect(toSavedLineupRequest(values({ match_time: "18:30" }), { id: "t" }).match_time).toBe(
      "18:30",
    );
  });

  it("sends the location, and leaves a blank one out", () => {
    const body = toSavedLineupRequest(values({ location: "Szeged, Alsóvárosi uszoda" }), {
      id: "t",
    });
    expect(body.location).toBe("Szeged, Alsóvárosi uszoda");
    expect(toSavedLineupRequest(values(), { id: "t" }).location).toBeUndefined();
  });

  it("sends is_home as chosen, or null for 'not said'", () => {
    expect(toSavedLineupRequest(values({ isHome: true }), { id: "t" }).is_home).toBe(true);
    expect(toSavedLineupRequest(values({ isHome: false }), { id: "t" }).is_home).toBe(false);
    expect(toSavedLineupRequest(values(), { id: "t" }).is_home).toBeNull();
  });

  it("does not put the location in the preview request", () => {
    expect(toLineupRequest(values({ location: "Szeged" }), "SZVTK")).not.toHaveProperty("location");
  });

  it("sends a free-text opponent by name", () => {
    const body = toSavedLineupRequest(values({ match_name: "Final" }), { id: "team-1" });
    expect(body).toMatchObject({ opponent_name: "Csongrád", match_name: "Final" });
    expect(body).not.toHaveProperty("source_opponent_id");
  });
});

const roster: Player[] = [
  { id: "p-1", team_id: "t", name: "Nagy Bence (new)", nssz_number: "N1b", created_at: "" },
];
const saved = (patch: Partial<SavedLineup> = {}): SavedLineup => ({
  id: "s-1",
  team_id: "t",
  team_name: "SZVTK",
  opponent_name: "Csongrád",
  match_name: "SZVTK - Csongrád",
  division: "OB I.",
  cap: "Kék",
  date: "2026. 10. 1.",
  match_date: null,
  match_time: null,
  location: null,
  is_home: null,
  coach: "Kovács",
  doctor: "Dr. Kis",
  assistant_coach: null,
  team_leader: null,
  ball_thrower: null,
  source_team_id: "t",
  source_opponent_id: null,
  created_at: "",
  updated_at: "",
  players: [
    { id: "x1", cap_number: 1, name: "Nagy Bence", nssz_number: "N1", source_player_id: "p-1" },
    { id: "x2", cap_number: 2, name: "Töröltem", nssz_number: "N2", source_player_id: "gone" },
    { id: "x3", cap_number: 11, name: "Kézi", nssz_number: "N11", source_player_id: null },
  ],
  ...patch,
});

describe("valuesFromSaved", () => {
  it("keeps the staff, division and players (each in their cap's row), not the match, and resets the date", () => {
    expect(valuesFromSaved(saved(), roster)).toEqual({
      ...emptyValues(),
      division: "OB I.",
      cap: "Kék",
      coach: "Kovács",
      doctor: "Dr. Kis",
      players: rows({
        1: { playerId: "p-1", name: "Nagy Bence (new)", nssz_number: "N1b" },
        2: { name: "Töröltem", nssz_number: "N2" },
        11: { name: "Kézi", nssz_number: "N11" },
      }),
    });
  });

  it("starts the clone on today with no time, whatever the saved lineup had", () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 24, 9, 0) });
    const clone = valuesFromSaved(saved({ match_date: "2026-10-01", match_time: "18:30" }), roster);
    vi.useRealTimers();
    expect(clone).toMatchObject({ match_date: "2026-11-24", match_time: "" });
  });

  it("keeps the location of the saved lineup", () => {
    expect(valuesFromSaved(saved({ location: "Szeged" }), roster).location).toBe("Szeged");
  });

  it("keeps the home/away side of the saved lineup, null for an old one", () => {
    expect(valuesFromSaved(saved({ is_home: true }), roster).isHome).toBe(true);
    expect(valuesFromSaved(saved({ is_home: false }), roster).isHome).toBe(false);
    expect(valuesFromSaved(saved({ is_home: null }), roster).isHome).toBeNull();
  });

  it("falls back to white caps for a colour it does not know", () => {
    expect(valuesFromSaved(saved({ cap: "?" }), roster).cap).toBe("Fehér");
  });
});

describe("valuesForEdit", () => {
  it("keeps everything the lineup holds, the match and opponent too", () => {
    const edit = valuesForEdit(
      saved({
        match_name: "Kupadöntő",
        source_opponent_id: "o-1",
        match_date: "2026-10-01",
        match_time: "18:30:00",
      }),
      roster,
    );
    expect(edit).toEqual({
      ...valuesFromSaved(saved(), roster),
      match_name: "Kupadöntő",
      opponent: "Csongrád",
      opponentId: "o-1",
      match_date: "2026-10-01",
      match_time: "18:30",
    });
  });

  it("leaves the default match name empty, so it follows a changed opponent", () => {
    expect(valuesForEdit(saved({ match_date: "2026-10-01" }), roster)).toMatchObject({
      match_name: "",
      opponentId: "",
      match_time: "",
    });
  });

  it("reads the printed date back for a lineup saved before the structured date", () => {
    expect(valuesForEdit(saved({ date: "2026. 10. 01. 18:30" }), roster)).toMatchObject({
      match_date: "2026-10-01",
      match_time: "18:30",
    });
  });

  it("leaves the date empty when the stored text is not a printed date", () => {
    expect(valuesForEdit(saved({ date: "next Sunday" }), roster)).toMatchObject({
      match_date: "",
      match_time: "",
    });
  });
});

describe("toSavedLineupUpdate", () => {
  const edited = values({
    match_date: "2026-10-01",
    match_time: "18:30",
    location: "Komjádi",
    isHome: true,
  });

  it("is the save body without team_id, keeps the lineup's own team and sends the version", () => {
    const body = toSavedLineupUpdate(
      edited,
      { source_team_id: "t-own", team_name: "SZVTK" },
      "2026-11-24T10:00:00.123456Z",
    );
    const created: Partial<ReturnType<typeof toSavedLineupRequest>> = toSavedLineupRequest(edited, {
      id: "t-current",
    });
    delete created.team_id;
    expect(body).toEqual({
      ...created,
      source_team_id: "t-own",
      is_home: true,
      expected_updated_at: "2026-11-24T10:00:00.123456Z",
    });
    expect(body).not.toHaveProperty("team_id");
    expect(body.location).toBe("Komjádi");
  });

  it("sends the stored team name when the lineup has no source team, and clears a blank location", () => {
    const body = toSavedLineupUpdate(
      { ...edited, location: "" },
      { source_team_id: null, team_name: "SZVTK" },
      "2026-11-24T10:00:00+00:00",
    );
    expect(body).toMatchObject({ team_name: "SZVTK", location: undefined });
    expect(body).not.toHaveProperty("source_team_id");
    expect(body.expected_updated_at).toBe("2026-11-24T10:00:00+00:00");
  });

  it("marks a version without a time zone as UTC, keeping its microseconds", () => {
    const body = toSavedLineupUpdate(
      edited,
      { source_team_id: "t", team_name: "SZVTK" },
      "2026-11-24T10:00:00.123456",
    );
    expect(body.expected_updated_at).toBe("2026-11-24T10:00:00.123456Z");
  });
});

describe("formPath", () => {
  const sent = values().players;

  it("maps API field names onto the creator's fields", () => {
    expect(formPath("opponent_name", sent)).toBe("opponent");
    expect(formPath("source_opponent_id", sent)).toBe("opponent");
    expect(formPath("match", sent)).toBe("match_name");
    expect(formPath("division", sent)).toBe("division");
  });

  it("maps the n-th sent player onto its cap row", () => {
    expect(formPath("players.1.source_player_id", sent)).toBe("players.3.name");
    expect(formPath("players.1.nssz_number", sent)).toBe("players.3.nssz_number");
  });
});
