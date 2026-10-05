import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { Skeleton } from "@/components/ui/skeleton";
import { TeamsProvider } from "@/features/teams/provider";

/**
 * Route guard for everything behind sign-in. While the stored session is being read it shows a
 * skeleton; with nobody signed in (or sign-in unconfigured) it sends the visitor to `/sign-in`,
 * remembering where they were going. Only a signed-in visitor reaches the routes below, wrapped
 * in {@link TeamsProvider} so they can read the user's teams.
 *
 * This is a convenience, not security: the API enforces access on every call.
 */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div role="status" aria-busy="true" aria-label="Loading" className="flex flex-col gap-4 p-8">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full max-w-2xl" />
      </div>
    );
  }
  if (status !== "signed-in") {
    const from = location.pathname + location.search + location.hash;
    return <Navigate to="/sign-in" replace state={{ from }} />;
  }
  return (
    <TeamsProvider>
      <Outlet />
    </TeamsProvider>
  );
}
