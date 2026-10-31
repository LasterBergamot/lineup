import type { components } from "@/api/schema";
import type { CreatorValues } from "@/features/creator/schema";
import type { Player } from "@/features/players/api";
import type { Team } from "@/features/teams/api";

type LineupRequest = components["schemas"]["LineupRequest"];
type SavedLineupCreate = components["schemas"]["SavedLineupCreate"];
type SavedLineup = components["schemas"]["SavedLineupResponse"];

/** The longest `match` the API accepts; "<team> - <opponent>" can exceed it, so it is cut. */
const MATCH_MAX = 200;

/** A blank optional field is left out of the request (the API prints it empty). */
const optional = (value: string) => value || undefined;

/** The empty creator: one free-text slot with cap number 1, white caps, nothing else filled in. */
export function emptyValues(): CreatorValues {
  return {
    match_name: "",
    opponent: "",
    opponentId: "",
    division: "",
    cap: "Fehér",
    date: "",
    coach: "",
    doctor: "",
    assistant_coach: "",
    team_leader: "",
    ball_thrower: "",
    players: [{ cap_number: 1, playerId: "", name: "", nssz_number: "" }],
  };
}

/**
 * The body for the stateless `POST /lineups` used by the preview. The match name defaults to
 * "<team> - <opponent>" like the saved-lineup endpoint does. Nothing here is stored.
 */
export function toLineupRequest(values: CreatorValues, teamName: string): LineupRequest {
  return {
    match: (values.match_name || `${teamName} - ${values.opponent}`).slice(0, MATCH_MAX),
    division: values.division,
    team_name: teamName,
    cap: values.cap,
    date: values.date,
    coach: values.coach,
    doctor: optional(values.doctor),
    assistant_coach: optional(values.assistant_coach),
    team_leader: optional(values.team_leader),
    ball_thrower: optional(values.ball_thrower),
    players: values.players.map((p) => ({
      cap_number: p.cap_number,
      name: p.name,
      nssz_number: p.nssz_number,
    })),
  };
}

/**
 * The body for `POST /lineups/saved`. The server takes the team name from `source_team_id`,
 * resolves a roster player or a listed opponent by id (as the caller, so a foreign id is a 404)
 * and freezes the values; the API wants exactly one of an id or free text per field.
 */
export function toSavedLineupRequest(
  values: CreatorValues,
  team: Pick<Team, "id">,
): SavedLineupCreate {
  return {
    team_id: team.id,
    source_team_id: team.id,
    ...(values.opponentId
      ? { source_opponent_id: values.opponentId }
      : { opponent_name: values.opponent }),
    match_name: optional(values.match_name),
    division: values.division,
    cap: values.cap,
    date: values.date,
    coach: values.coach,
    doctor: optional(values.doctor),
    assistant_coach: optional(values.assistant_coach),
    team_leader: optional(values.team_leader),
    ball_thrower: optional(values.ball_thrower),
    players: values.players.map((p) =>
      p.playerId
        ? { source_player_id: p.playerId, cap_number: p.cap_number }
        : { name: p.name, nssz_number: p.nssz_number, cap_number: p.cap_number },
    ),
  };
}

/**
 * Starting values for "Clone to new match": the staff, division, cap colour and players of a
 * saved lineup, with the match, opponent and date left empty. A player who is still on the roster
 * is picked from it (so name changes follow); one who was deleted since stays as typed-in text
 * with the frozen name and NSSZ number.
 */
export function valuesFromSaved(saved: SavedLineup, roster: readonly Player[]): CreatorValues {
  const onRoster = new Map(roster.map((p) => [p.id, p]));
  return {
    ...emptyValues(),
    division: saved.division,
    cap: saved.cap === "Kék" ? "Kék" : "Fehér",
    coach: saved.coach,
    doctor: saved.doctor ?? "",
    assistant_coach: saved.assistant_coach ?? "",
    team_leader: saved.team_leader ?? "",
    ball_thrower: saved.ball_thrower ?? "",
    players: saved.players.map((p) => {
      const current = p.source_player_id ? onRoster.get(p.source_player_id) : undefined;
      return {
        cap_number: p.cap_number,
        playerId: current?.id ?? "",
        name: current?.name ?? p.name,
        nssz_number: current?.nssz_number ?? p.nssz_number,
      };
    }),
  };
}

/** Narrows router state to a saved lineup the Saved page handed over (anything else is ignored). */
export function isSavedLineup(value: unknown): value is SavedLineup {
  const candidate = value as Partial<SavedLineup> | null | undefined;
  return typeof candidate?.id === "string" && Array.isArray(candidate.players);
}

/**
 * Maps a field path from a server 422 onto the creator's form fields: the API calls the opponent
 * `opponent_name` / `source_opponent_id`, the preview endpoint calls the match `match`, and a bad
 * roster player id is shown under that slot's name.
 */
export function formPath(path: string): string {
  return path
    .replace(/^(opponent_name|source_opponent_id)$/, "opponent")
    .replace(/^match$/, "match_name")
    .replace(/^players\.(\d+)\.source_player_id$/, "players.$1.name");
}
