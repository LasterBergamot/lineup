import { createContext, useContext } from "react";

export type ToastKind = "success" | "info" | "error";

/** How long a success or info toast stays; an error stays until it is dismissed. */
export const TOAST_MS = 5000;
/** At most this many toasts are on screen; a new one pushes the oldest out. */
export const MAX_TOASTS = 3;

/** Carries the `toast()` function from `ToastProvider` to {@link useToast}. */
export const ToastContext = createContext<((kind: ToastKind, message: string) => void) | null>(
  null,
);

/**
 * Raises a short notice that does not block anything: `toast("success", t("…"))`. The message is
 * shown in a polite live region (errors announce at once) and held in memory only, never in
 * storage, so it must be generic text such as "Lineup saved": never a player's name or NSSZ number.
 * Must be used below `ToastProvider`.
 */
export function useToast() {
  const toast = useContext(ToastContext);
  if (!toast) throw new Error("useToast must be used inside <ToastProvider>");
  return toast;
}
