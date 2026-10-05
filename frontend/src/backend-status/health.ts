import { api } from "@/api/client";

/**
 * - `ok`: 200.
 * - `unavailable`: the API answered 503 to the readiness check, meaning it is up but its
 *   database is not (e.g. a paused free-tier project).
 * - `transient`: no answer or a gateway error (502/503/504); worth retrying.
 * - `fatal`: any other answer; retrying would just repeat it.
 */
export type ProbeResult = "ok" | "unavailable" | "transient" | "fatal";

/** Resolves a `/health` probe; `db` adds the database readiness check (`?db=1`). */
export type Probe = (db: boolean, signal: AbortSignal) => Promise<ProbeResult>;

/** How long one probe may take; a booting Fly machine holds the request, so this is generous. */
export const PROBE_TIMEOUT_MS = 20_000;

/** Give up on a sleeping backend after this long and report it as down. */
export const GIVE_UP_AFTER_MS = 60_000;

/** Pauses between liveness attempts; the last value repeats. */
export const RETRY_DELAYS_MS = [1000, 2000, 3000, 5000];

/** Builds a probe on top of an API client (injectable so tests can point it at a stub server). */
export function createProbe(client: Pick<typeof api, "GET"> = api): Probe {
  return async (db, signal) => {
    try {
      const { response } = await client.GET("/health", {
        params: { query: db ? { db: true } : {} },
        signal: AbortSignal.any([signal, AbortSignal.timeout(PROBE_TIMEOUT_MS)]),
      });
      if (response.ok) return "ok";
      if (response.status === 503 && db) return "unavailable";
      return [502, 503, 504].includes(response.status) ? "transient" : "fatal";
    } catch {
      return "transient";
    }
  };
}

/** Asks the API how it is. Never throws: every failure is folded into a {@link ProbeResult}. */
export const probeHealth: Probe = createProbe();

function sleepFor(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

interface WaitOptions {
  signal: AbortSignal;
  probe?: Probe;
  sleep?: (ms: number, signal: AbortSignal) => Promise<void>;
  now?: () => number;
}

/**
 * Polls the liveness endpoint until the API answers. Returns `"ready"` on the first 200 and
 * `"down"` on a non-retryable answer or after {@link GIVE_UP_AFTER_MS}. Checking `/health`
 * first also starts a sleeping machine booting while the user is still looking at the page.
 * Returns early (as `"down"`) when `signal` aborts; callers ignore the result in that case.
 */
export async function waitForBackend({
  signal,
  probe = probeHealth,
  sleep = sleepFor,
  now = Date.now,
}: WaitOptions): Promise<"ready" | "down"> {
  const startedAt = now();
  for (let attempt = 0; ; attempt++) {
    const result = await probe(false, signal);
    if (result === "ok") return "ready";
    if (signal.aborted || result !== "transient" || now() - startedAt >= GIVE_UP_AFTER_MS) {
      return "down";
    }
    await sleep(RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)]!, signal);
  }
}
