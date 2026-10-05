import type { UseQueryResult } from "@tanstack/react-query";
import { createContext, useContext } from "react";
import type { Team } from "@/features/teams/api";

export interface TeamsValue {
  /** The user's teams (loading / error / data states for a `QueryBoundary`). */
  query: UseQueryResult<Team[]>;
  /** The team the app is showing. Until team switching exists, the first one by name. */
  current: Team | undefined;
}

export const TeamsContext = createContext<TeamsValue | null>(null);

/** The signed-in user's teams. Must be used inside `TeamsProvider`. */
export function useTeams(): TeamsValue {
  const value = useContext(TeamsContext);
  if (!value) throw new Error("useTeams must be used inside TeamsProvider");
  return value;
}
