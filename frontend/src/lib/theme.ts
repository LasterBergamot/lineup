import { useCallback, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "lineup-theme";

function currentTheme(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

/**
 * Light/dark state backed by the `dark` class on `<html>` (what Tailwind's `dark:` variant and
 * the CSS tokens key off). The initial class is set before first paint by `public/theme-init.js`,
 * so this only reads it. The choice is kept in localStorage (strictly necessary UI preference).
 */
export function useTheme(): { theme: Theme; toggle: () => void } {
  const [theme, setTheme] = useState<Theme>(currentTheme);

  const toggle = useCallback(() => {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage can be blocked; the theme still applies for this page view.
    }
    setTheme(next);
  }, []);

  return { theme, toggle };
}
