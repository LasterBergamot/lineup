import { useEffect, useState } from "react";

/**
 * True once `active` has stayed true for `delayMs`; false again as soon as it ends. Used for
 * "this is taking a while" messages that should not flash up for fast requests.
 */
export function useAfterDelay(active: boolean, delayMs: number): boolean {
  const [elapsed, setElapsed] = useState(false);
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => setElapsed(true), delayMs);
    return () => {
      clearTimeout(timer);
      setElapsed(false);
    };
  }, [active, delayMs]);
  return active && elapsed;
}
