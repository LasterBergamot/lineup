import { useEffect, useState } from "react";

/**
 * `value`, but only once it has stopped changing for `delayMs`. Used for search-as-you-type, so
 * a request goes out when the user pauses rather than on every keystroke. The first render
 * returns `value` straight away, so an initial (e.g. blank) search needs no wait.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
