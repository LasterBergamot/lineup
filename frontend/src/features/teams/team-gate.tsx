import type { ReactNode } from "react";
import { QueryBoundary } from "@/components/query-boundary";
import { Skeleton } from "@/components/ui/skeleton";
import { Onboarding } from "@/features/teams/onboarding";
import { useTeams } from "@/features/teams/context";

/**
 * Shows the page only once the user has a team; a user with none gets {@link Onboarding}. While
 * the team list loads the shell is already on screen with a skeleton here, and a failed load
 * (including the API answering 503 when it can't check tokens) shows the retry box rather than
 * bouncing the user back to sign-in: a 503 says the service is down, not that they are signed out.
 */
export function TeamGate({ children }: { children: ReactNode }) {
  const { query } = useTeams();
  return (
    <QueryBoundary
      query={query}
      skeleton={
        <div className="flex flex-col gap-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-40 w-full max-w-2xl" />
        </div>
      }
    >
      {(teams) => (teams.length === 0 ? <Onboarding /> : children)}
    </QueryBoundary>
  );
}
