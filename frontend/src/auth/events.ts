type Listener = () => void;

const listeners = new Set<Listener>();

/**
 * Called by the API client when a request that carried a token comes back `401`. The auth
 * provider listens and signs the user out, so an expired or revoked session sends them to the
 * sign-in page instead of leaving every region showing an error.
 */
export function notifyUnauthorized(): void {
  for (const listener of [...listeners]) listener();
}

/** Subscribes to {@link notifyUnauthorized}; returns the unsubscribe function. */
export function onUnauthorized(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
