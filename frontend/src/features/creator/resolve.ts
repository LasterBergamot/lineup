import type { components } from "@/api/schema";
import type { CreatorValues } from "@/features/creator/schema";
import type { Player } from "@/features/players/api";
import type { StaffRole } from "@/features/staff/api";
import type { Team } from "@/features/teams/api";
import { composeMatchDate, parseMatchDate, todayIso } from "@/lib/match-date";
import { capRows, filledRows, requestPlayers, rowPath } from "@/features/lineup/cap-rows";

type LineupRequest = components["schemas"]["LineupRequest"];
type SavedLineupCreate = components["schemas"]["SavedLineupCreate"];
type SavedLineupUpdate = components["schemas"]["SavedLineupUpdate"];
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
    isHome: null,
    match_date: todayIso(),
    match_time: "",
    location: "",
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
  return { team_id: team.id, source_team_id: team.id, ...lineupFields(values) };
}

/** What a new lineup and an edit send alike: everything but the team. */
function lineupFields(values: CreatorValues) {
  return {
    ...(values.opponentId
      ? { source_opponent_id: values.opponentId }
      : { opponent_name: values.opponent }),
    match_name: optional(values.match_name),
    division: values.division,
    cap: values.cap,
    is_home: values.isHome,
    match_date: values.match_date,
    match_time: optional(values.match_time),
    location: optional(values.location),
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
 * The body for `PUT /lineups/saved/{id}` (#290): the same fields as {@link toSavedLineupRequest},
 * without `team_id` (a lineup never moves to another team), plus `expected_updated_at`, the
 * version the form was loaded from (a 409 if someone saved since). The team name keeps coming from
 * the lineup's own source team (or its stored text), so an edit never swaps the team. Every field
 * is replaced, so a blank optional field (the location, a staff role) clears the stored value. The
 * Home / Away toggle's value (`isHome`, #296) goes along with the other fields.
 */
export function toSavedLineupUpdate(
  values: CreatorValues,
  saved: Pick<SavedLineup, "source_team_id" | "team_name">,
  expectedUpdatedAt: string,
): SavedLineupUpdate {
  return {
    ...lineupFields(values),
    ...(saved.source_team_id
      ? { source_team_id: saved.source_team_id }
      : { team_name: saved.team_name }),
    expected_updated_at: withZone(expectedUpdatedAt),
  };
}

/**
 * The API wants `expected_updated_at` with a time zone. It returns one, but a bare value (SQLite
 * can hand one back) is UTC, so "Z" is appended. The text is otherwise sent back as it came: going
 * through `Date` would drop the microseconds and make every edit a 409.
 */
const withZone = (value: string) => (/(Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`);

/**
 * Starting values for "Edit" (#290): everything the saved lineup holds, so saving it unchanged
 * keeps it as it is. The match name stays empty when it is the default "<team> - <opponent>" the
 * API made, so it follows a changed opponent again. A lineup saved before the structured date
 * (#287) has its printed `date` read back with `parseMatchDate()`; text that is not a printed date
 * leaves the date empty, and the form asks for one. The players and staff are as for a clone: a
 * roster player still on the roster is picked again (their current name is shown and saved), one
 * deleted since stays as typed-in text.
 */
export function valuesForEdit(saved: SavedLineup, roster: readonly Player[]): CreatorValues {
  const printed = saved.match_date ? null : parseMatchDate(saved.date);
  return {
    ...valuesFromSaved(saved, roster),
    match_name:
      saved.match_name === `${saved.team_name} - ${saved.opponent_name}` ? "" : saved.match_name,
    opponent: saved.opponent_name,
    opponentId: saved.source_opponent_id ?? "",
    match_date: saved.match_date ?? printed?.date ?? "",
    // The API sends `HH:MM:SS`; the time input holds `HH:MM`.
    match_time: saved.match_time?.slice(0, 5) ?? printed?.time ?? "",
  };
}

/**
 * Starting values for "Clone to new match": the staff, division, cap colour, home/away side and players of a
 * saved lineup, with the match and opponent left empty (the location is kept, as a venue is often reused), the date reset to today and the time cleared (it is a
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
    isHome: saved.is_home,
    location: saved.location ?? "",
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
