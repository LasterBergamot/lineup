import type { CAP_COLOURS } from "@/features/lineup/schema";

/** The Home / Away toggle's two choices; the form stores them as `is_home` (`true`, `false`, or `null` for "not said"). */
export const SIDES = ["home", "away"] as const;
export type Side = (typeof SIDES)[number];

/** The toggle's selection for an `is_home` value; `""` selects neither (an old lineup, or not chosen yet). */
export const sideOf = (isHome: boolean | null): Side | "" =>
  isHome === null ? "" : isHome ? "home" : "away";

/** The cap colour that goes with a side: the home team plays in white, the away team in blue. */
export const capFor = (isHome: boolean): (typeof CAP_COLOURS)[number] => (isHome ? "Fehér" : "Kék");

/** The separator of a match name such as `SZVTK - Csongrád`. */
const SEPARATOR = " - ";

/**
 * The suggested match name, home team first: `<team> - <opponent>` at home, `<opponent> - <team>`
 * away. Blank (so the field falls back to the server default) until the opponent is known.
 */
export function suggestMatchName(team: string, opponent: string, isHome: boolean): string {
  const rival = opponent.trim();
  if (!rival) return "";
  return isHome ? `${team}${SEPARATOR}${rival}` : `${rival}${SEPARATOR}${team}`;
}

/**
 * Puts `team` on the home or away side of a typed match name. The Quick sheet has no opponent
 * field, so this only reorders a name of the form `A - B` where one side is the team (ignoring
 * case); anything else is returned as it was.
 */
export function orderMatchName(match: string, team: string, isHome: boolean): string {
  const parts = match.split(SEPARATOR).map((part) => part.trim());
  const name = team.trim().toLowerCase();
  if (parts.length !== 2 || !name) return match;
  const [first, second] = parts as [string, string];
  const teamFirst = first.toLowerCase() === name;
  if (!teamFirst && second.toLowerCase() !== name) return match;
  const [rival, own] = teamFirst ? [second, first] : [first, second];
  return isHome ? `${own}${SEPARATOR}${rival}` : `${rival}${SEPARATOR}${own}`;
}
