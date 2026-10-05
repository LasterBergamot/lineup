import { Button } from "@/components/ui/button";
import { useBackendStatus } from "@/backend-status/context";

/** `VITE_COLD_START_NOTICE=false` turns the wake-up message off (e.g. on always-on hosting). */
function coldStartNoticeEnabled(): boolean {
  return import.meta.env.VITE_COLD_START_NOTICE !== "false";
}

/**
 * Non-blocking notice above the page content. The page itself keeps rendering; this only
 * explains why data regions are still showing skeletons:
 * - while the free-tier API wakes up (behind `VITE_COLD_START_NOTICE`),
 * - when its database is paused,
 * - when the API cannot be reached at all.
 */
export function BackendStatusBanner() {
  const { status, elapsedSeconds, retry } = useBackendStatus();

  if (status === "waking" && coldStartNoticeEnabled()) {
    return (
      <div role="status" className="border-b bg-warning px-4 py-3 text-sm text-warning-foreground">
        The server is starting up — this can take up to ~30 seconds on our free hosting. Thanks for
        your patience.
        <span className="ml-2 tabular-nums opacity-80">{`(${elapsedSeconds} s)`}</span>
      </div>
    );
  }
  if (status === "db-paused") {
    return (
      <div role="alert" className="border-b bg-warning px-4 py-3 text-sm text-warning-foreground">
        The database is paused (free tier). Ask the app administrator to resume it; saved data is
        unavailable until then.
      </div>
    );
  }
  if (status === "down") {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center gap-3 border-b bg-destructive px-4 py-3 text-sm text-destructive-foreground"
      >
        We can&apos;t reach the server right now.
        <Button size="sm" variant="outline" className="text-foreground" onClick={retry}>
          Try again
        </Button>
      </div>
    );
  }
  return null;
}
