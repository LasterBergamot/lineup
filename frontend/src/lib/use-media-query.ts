import { useCallback, useSyncExternalStore } from "react";

/**
 * Whether a CSS media query matches, kept current as the window resizes. Where `matchMedia`
 * does not exist (a test DOM) the answer is `fallback`, so the caller picks which layout the
 * environment without a screen gets.
 */
export function useMediaQuery(query: string, fallback: boolean): boolean {
  // A stable `subscribe` per query: a new function each render would resubscribe every time.
  const subscribe = useCallback(
    (notify: () => void) => {
      if (!window.matchMedia) return () => {};
      const list = window.matchMedia(query);
      list.addEventListener("change", notify);
      return () => list.removeEventListener("change", notify);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () =>
    window.matchMedia ? window.matchMedia(query).matches : fallback,
  );
}
