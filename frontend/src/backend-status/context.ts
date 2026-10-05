import { createContext, useContext } from "react";

/**
 * Where the backend is in its wake-up cycle:
 * - `unknown`: the first `/health` check is still fresh (under ~1.5 s), so nothing is shown yet.
 * - `waking`: no answer yet; the free-tier machine is probably booting.
 * - `ready`: the API answers.
 * - `db-paused`: the API answers but its database does not (free-tier Supabase pause).
 * - `down`: no answer after about a minute, or a non-retryable error.
 */
export type BackendStatus = "unknown" | "waking" | "ready" | "db-paused" | "down";

export interface BackendStatusValue {
  status: BackendStatus;
  /** Whole seconds since the first check started; only meaningful while `waking`. */
  elapsedSeconds: number;
  /** Starts the wake-up check again (used by the "Try again" button when `down`). */
  retry: () => void;
}

export const BackendStatusContext = createContext<BackendStatusValue | null>(null);

/** Current backend status. Must be used inside `BackendStatusProvider`. */
export function useBackendStatus(): BackendStatusValue {
  const value = useContext(BackendStatusContext);
  if (!value) throw new Error("useBackendStatus must be used inside BackendStatusProvider");
  return value;
}
