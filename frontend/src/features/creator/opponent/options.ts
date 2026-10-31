import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useAuth } from "@/auth/context";
import { listRecentOpponents, recentOpponentsKey } from "@/features/creator/opponent/api";
import { poolKey, searchPool, type PoolTeam } from "@/features/directory/api";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** One suggestion in the opponent combobox. */
export interface OpponentOption {
  name: string;
  /** `directory`: a listed team (it has an id); `recent`: a name from this team's saved lineups. */
  source: "recent" | "directory";
  /** Set for directory teams only: sent as `source_opponent_id` when the user picks it. */
  directoryId?: string;
}

/** How many directory teams one search asks for; the API allows up to 100. */
const DIRECTORY_LIMIT = 20;
/** Pause in typing before a directory search goes out. */
export const SEARCH_DELAY_MS = 300;
/** The API's limit on the directory `search` term. */
const MAX_SEARCH_LENGTH = 120;
/** The API's limit on an opponent name (`opponent_name`). */
export const MAX_OPPONENT_LENGTH = 120;

/** The directory team whose name `value` is (trimmed, case-insensitive), if there is one. */
export function findDirectoryMatch(
  options: readonly OpponentOption[],
  value: string,
): { directoryId: string } | undefined {
  const wanted = value.trim().toLowerCase();
  const hit = options.find(
    (option) => option.directoryId !== undefined && option.name.trim().toLowerCase() === wanted,
  );
  return hit?.directoryId === undefined ? undefined : { directoryId: hit.directoryId };
}

/**
 * Merges the two sources into one list without duplicate names (compared trimmed and
 * case-insensitively). Directory teams come first and win a tie, so a name that is both recent
 * and listed keeps its id. The caller's own team is left out: a team does not play itself.
 */
export function mergeOpponentOptions(
  recent: readonly string[],
  directory: readonly PoolTeam[],
  ownTeamId: string,
): OpponentOption[] {
  const seen = new Set<string>();
  const options: OpponentOption[] = [];
  const add = (option: OpponentOption) => {
    const key = option.name.trim().toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    options.push(option);
  };
  for (const team of directory) {
    if (team.id !== ownTeamId) add({ name: team.name, source: "directory", directoryId: team.id });
  }
  for (const name of recent) add({ name, source: "recent" });
  return options;
}

/**
 * The suggestions for the opponent field of `teamId`'s lineup while the user types `term`: the
 * team's recent opponents plus the listed directory teams matching the term (searched after a
 * 300 ms pause). The term stays in memory (the query key), never in the URL, storage or a log.
 * A failed request just means fewer suggestions: free text always works.
 */
export function useOpponentOptions(teamId: string, term: string): OpponentOption[] {
  const { userId } = useAuth();
  const search = useDebouncedValue(term.trim().slice(0, MAX_SEARCH_LENGTH), SEARCH_DELAY_MS);
  const recent = useQuery({
    queryKey: recentOpponentsKey(userId, teamId),
    queryFn: () => listRecentOpponents(teamId),
    // Both requests need a signed-in caller; waiting also avoids a key that belongs to no one.
    enabled: userId !== null,
  });
  const directory = useQuery({
    queryKey: poolKey(userId, search),
    queryFn: () => searchPool(search, DIRECTORY_LIMIT),
    // Keep the last suggestions while the next search runs, so the list does not flicker.
    placeholderData: keepPreviousData,
    enabled: userId !== null,
  });
  return mergeOpponentOptions(recent.data ?? [], directory.data ?? [], teamId);
}
