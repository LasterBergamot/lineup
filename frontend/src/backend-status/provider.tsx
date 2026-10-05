import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { waitForBackend, probeHealth, type Probe } from "@/backend-status/health";
import { BackendStatusContext, type BackendStatus } from "@/backend-status/context";

/** No answer after this long means "the server is probably waking up", so the banner may show. */
export const WAKING_AFTER_MS = 1500;

/**
 * Checks `GET /health` as soon as the app loads (even before sign-in, so a sleeping backend
 * starts booting while the user is still on the first screen), and tells the rest of the
 * tree what state the backend is in. Once it answers, one more `?db=1` check looks for a
 * paused database without blocking the UI.
 */
export function BackendStatusProvider({
  children,
  probe = probeHealth,
}: {
  children: ReactNode;
  probe?: Probe;
}) {
  const [status, setStatus] = useState<BackendStatus>("unknown");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [run, setRun] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const startedAt = Date.now();
    const wakingTimer = setTimeout(
      () => setStatus((current) => (current === "unknown" ? "waking" : current)),
      WAKING_AFTER_MS,
    );
    const ticker = setInterval(
      () => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );

    void (async () => {
      const liveness = await waitForBackend({ signal, probe });
      clearTimeout(wakingTimer);
      clearInterval(ticker);
      if (signal.aborted) return;
      setStatus(liveness === "ready" ? "ready" : "down");
      if (liveness !== "ready") return;
      const readiness = await probe(true, signal);
      if (!signal.aborted && readiness === "unavailable") setStatus("db-paused");
    })();

    return () => {
      controller.abort();
      clearTimeout(wakingTimer);
      clearInterval(ticker);
    };
  }, [probe, run]);

  const retry = useCallback(() => {
    setStatus("unknown");
    setElapsedSeconds(0);
    setRun((n) => n + 1);
  }, []);

  const value = useMemo(() => ({ status, elapsedSeconds, retry }), [status, elapsedSeconds, retry]);
  return <BackendStatusContext.Provider value={value}>{children}</BackendStatusContext.Provider>;
}
