import { QueryClient } from "@tanstack/react-query";
import { isTransient } from "@/api/errors";

/** About 47 s of retrying in total with the delays below, matching the ~60 s cold start budget. */
export const MAX_RETRIES = 8;

/** Retry only transient failures (see `isTransient`); a 4xx is an answer, not a hiccup. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return isTransient(error) && failureCount < MAX_RETRIES;
}

/** Exponential backoff: 1 s, 2 s, 4 s, then 8 s between attempts. */
export function retryDelay(failureCount: number): number {
  return Math.min(1000 * 2 ** failureCount, 8000);
}

/**
 * The app-wide query client. Queries retry transient failures so the UI rides out a cold
 * start; mutations never retry on their own, because repeating a save or a PDF render the
 * user did not ask for twice is worse than showing an error.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, retryDelay, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
