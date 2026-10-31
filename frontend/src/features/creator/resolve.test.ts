import type { components } from "@/api/schema";
import {
  emptyValues,
  formPath,
  toLineupRequest,
  toSavedLineupRequest,
  valuesFromSaved,
} from "@/features/creator/resolve";
import type { CreatorValues } from "@/features/creator/schema";
import type { Player } from "@/features/players/api";

type SavedLineup = components["schemas"]["SavedLineupResponse"];

const values = (patch: Partial<CreatorValues> = {}): CreatorValues => ({
  ...emptyValues(),
  opponent: "Csongrád",
  division: "OB I.",
  date: "2026. 11. 1.",
  coach: "Kovács",
  players: [
    { cap_number: 1, playerId: "p-1", name: "Nagy Bence", nssz_number: "N1" },
    { cap_number: 2, playerId: "", name: "Kiss Ádám", nssz_number: "N2" },
  ],
  ...patch,
});

describe("emptyValues", () => {
  it("starts with white caps and one empty typed-in slot", () => {
    expect(emptyValues()).toMatchObject({
      cap: "Fehér",
      players: [{ cap_number: 1, playerId: "", name: "", nssz_number: "" }],
    });
  });
});

describe("toLineupRequest", () => {
  it("names the match after the teams and prints the players as they stand", () => {
    const body = toLineupRequest(values(), "SZVTK");
    expect(body).toMatchObject({
      match: "SZVTK - Csongrád",
      team_name: "SZVTK",
      coach: "Kovács",
      players: [
        { cap_number: 1, name: "Nagy Bence", nssz_number: "N1" },
        { cap_number: 2, name: "Kiss Ádám", nssz_number: "N2" },
      ],
    });
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
  it("sends roster players and a listed opponent as ids", () => {
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
        { name: "Kiss Ádám", nssz_number: "N2", cap_number: 2 },
      ],
    });
    expect(body).not.toHaveProperty("opponent_name");
    expect(body.match_name).toBeUndefined();
    expect(body.doctor).toBeUndefined();
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
  coach: "Kovács",
  doctor: "Dr. Kis",
  assistant_coach: null,
  team_leader: null,
  ball_thrower: null,
  source_team_id: "t",
  source_opponent_id: null,
  created_at: "",
  players: [
    { id: "x1", cap_number: 1, name: "Nagy Bence", nssz_number: "N1", source_player_id: "p-1" },
    { id: "x2", cap_number: 2, name: "Töröltem", nssz_number: "N2", source_player_id: "gone" },
    { id: "x3", cap_number: 3, name: "Kézi", nssz_number: "N3", source_player_id: null },
  ],
  ...patch,
});

describe("valuesFromSaved", () => {
  it("keeps the staff, division and players but not the match, opponent or date", () => {
    expect(valuesFromSaved(saved(), roster)).toEqual({
      ...emptyValues(),
      division: "OB I.",
      cap: "Kék",
      coach: "Kovács",
      doctor: "Dr. Kis",
      players: [
        { cap_number: 1, playerId: "p-1", name: "Nagy Bence (new)", nssz_number: "N1b" },
        { cap_number: 2, playerId: "", name: "Töröltem", nssz_number: "N2" },
        { cap_number: 3, playerId: "", name: "Kézi", nssz_number: "N3" },
      ],
    });
  });

  it("falls back to white caps for a colour it does not know", () => {
    expect(valuesFromSaved(saved({ cap: "?" }), roster).cap).toBe("Fehér");
  });
});

describe("formPath", () => {
  it("maps API field names onto the creator's fields", () => {
    expect(formPath("opponent_name")).toBe("opponent");
    expect(formPath("source_opponent_id")).toBe("opponent");
    expect(formPath("match")).toBe("match_name");
    expect(formPath("players.3.source_player_id")).toBe("players.3.name");
    expect(formPath("players.3.nssz_number")).toBe("players.3.nssz_number");
    expect(formPath("division")).toBe("division");
  });
});
