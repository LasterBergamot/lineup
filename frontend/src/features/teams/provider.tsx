import { useQuery } from "@tanstack/react-query";
import { useMemo, type ReactNode } from "react";
import { useAuth } from "@/auth/context";
import { listTeams, teamsKey } from "@/features/teams/api";
import { TeamsContext } from "@/features/teams/context";

/**
 * Loads the signed-in user's teams once for the whole app shell. Everything that needs "the
 * team" (the account panel, the onboarding gate, later the roster) reads it from here.
 */
export function TeamsProvider({ children }: { children: ReactNode }) {
  const { userId } = useAuth();
  const query = useQuery({
    queryKey: teamsKey(userId),
    queryFn: () => listTeams(),
    enabled: userId !== null,
  });
  const value = useMemo(() => ({ query, current: query.data?.[0] }), [query]);
  return <TeamsContext.Provider value={value}>{children}</TeamsContext.Provider>;
}
