import type { components } from "@/api/schema";
import type { CreatorValues } from "@/features/creator/schema";
import type { Player } from "@/features/players/api";
import type { StaffRole } from "@/features/staff/api";
import type { Team } from "@/features/teams/api";
import { composeMatchDate, todayIso } from "@/lib/match-date";
import { capRows, filledRows, requestPlayers, rowPath } from "@/features/lineup/cap-rows";

type LineupRequest = components["schemas"]["LineupRequest"];
type SavedLineupCreate = components["schemas"]["SavedLineupCreate"];
type SavedLineup = components["schemas"]["SavedLineupResponse"];

/** The longest `match` the API accepts; "<team> - <opponent>" can exceed it, so it is cut. */
const MATCH_MAX = 200;

/** A blank optional field is left out of the request (the API prints it empty). */
const optional = (value: string) => value || undefined;

/**
 * The empty creator: the 15 empty cap rows, white caps, nothing else filled in except the
 * team's default division (`division`, when it has one; still editable per lineup), each staff
 * role's default name (`staff`, #289; a role without one stays empty), and the match date set to
 * today (the browser's local day, read on each call) with no start time.
 */
export function emptyValues(
  division = "",
  staff: Partial<Record<StaffRole, string>> = {},
): CreatorValues {
  return {
    match_name: "",
    opponent: "",
    opponentId: "",
    division,
    cap: "Fehér",
    match_date: todayIso(),
    match_time: "",
    coach: staff.coach ?? "",
    doctor: "",
    assistant_coach: staff.assistant_coach ?? "",
    team_leader: staff.team_leader ?? "",
    ball_thrower: staff.ball_thrower ?? "",
    players: capRows((cap_number) => ({ cap_number, playerId: "", name: "", nssz_number: "" })),
  };
}

/**
 * The body for the stateless `POST /lineups` used by the preview. The match name defaults to
 * "<team> - <opponent>" like the saved-lineup endpoint does. Empty cap rows are left out.
 * Nothing here is stored.
 */
export function toLineupRequest(values: CreatorValues, teamName: string): LineupRequest {
  return {
    match: (values.match_name || `${teamName} - ${values.opponent}`).slice(0, MATCH_MAX),
    division: values.division,
    team_name: teamName,
    cap: values.cap,
    date: composeMatchDate(values.match_date, values.match_time),
    coach: values.coach,
    doctor: optional(values.doctor),
    assistant_coach: optional(values.assistant_coach),
    team_leader: optional(values.team_leader),
    ball_thrower: optional(values.ball_thrower),
    players: requestPlayers(values.players),
  };
}

/**
 * The body for `POST /lineups/saved`. The server takes the team name from `source_team_id`,
 * resolves a roster player or a listed opponent by id (as the caller, so a foreign id is a 404)
 * and freezes the values; the API wants exactly one of an id or free text per field. The date goes
 * as `match_date`/`match_time` and the server composes the printed text. Empty cap rows are left
 * out.
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
    match_date: values.match_date,
    match_time: optional(values.match_time),
    coach: values.coach,
    doctor: optional(values.doctor),
    assistant_coach: optional(values.assistant_coach),
    team_leader: optional(values.team_leader),
    ball_thrower: optional(values.ball_thrower),
    players: filledRows(values.players).map((p) =>
      p.playerId
        ? { source_player_id: p.playerId, cap_number: p.cap_number }
        : { name: p.name.trim(), nssz_number: p.nssz_number.trim(), cap_number: p.cap_number },
    ),
  };
}

/**
 * Starting values for "Clone to new match": the staff, division, cap colour and players of a
 * saved lineup, with the match and opponent left empty, the date reset to today and the time cleared (it is a
 * new match). Each player goes into the row of
 * their `cap_number`; the other rows stay empty. A player who is still on the roster is picked
 * from it (so name changes follow); one who was deleted since stays as typed-in text with the
 * frozen name and NSSZ number.
 */
export function valuesFromSaved(saved: SavedLineup, roster: readonly Player[]): CreatorValues {
  const onRoster = new Map(roster.map((p) => [p.id, p]));
  const byCap = new Map(saved.players.map((p) => [p.cap_number, p]));
  return {
    ...emptyValues(),
    division: saved.division,
    cap: saved.cap === "Kék" ? "Kék" : "Fehér",
    coach: saved.coach,
    doctor: saved.doctor ?? "",
    assistant_coach: saved.assistant_coach ?? "",
    team_leader: saved.team_leader ?? "",
    ball_thrower: saved.ball_thrower ?? "",
    players: capRows((cap_number) => {
      const p = byCap.get(cap_number);
      const current = p?.source_player_id ? onRoster.get(p.source_player_id) : undefined;
      return {
        cap_number,
        playerId: current?.id ?? "",
        name: current?.name ?? p?.name ?? "",
        nssz_number: current?.nssz_number ?? p?.nssz_number ?? "",
      };
    }),
  };
}

/**
 * Maps a field path from a server 422 onto the creator's form fields: the API calls the opponent
 * `opponent_name` / `source_opponent_id`, the preview endpoint calls the match `match`, a bad
 * roster player id is shown under that slot's name, and `players.<n>` (the n-th filled row in the
 * request) becomes that row's index in `rows`, the values that were sent.
 */
export function formPath(path: string, rows: CreatorValues["players"]): string {
  return rowPath(path, rows)
    .replace(/^(opponent_name|source_opponent_id)$/, "opponent")
    .replace(/^match$/, "match_name")
    .replace(/^players\.(\d+)\.source_player_id$/, "players.$1.name");
}
