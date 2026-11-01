import { CircleAlert, CircleCheck, Info, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { MAX_TOASTS, TOAST_MS, ToastContext, type ToastKind } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

/**
 * Owns the toast stack and renders it in a fixed live region (above the bottom navigation on a
 * phone). Success and info toasts dismiss themselves after {@link TOAST_MS}, pausing while the
 * pointer or keyboard focus is on them; errors stay until dismissed; at most {@link MAX_TOASTS}
 * show at once.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const toast = useCallback((kind: ToastKind, message: string) => {
    setItems((current) => [...current, { id: nextId.current++, kind, message }].slice(-MAX_TOASTS));
  }, []);
  const dismiss = useCallback(
    (id: number) => setItems((current) => current.filter((item) => item.id !== id)),
    [],
  );

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div
        role="region"
        aria-label={t("toast.region")}
        aria-live="polite"
        className="pointer-events-none fixed inset-x-4 bottom-20 z-[60] flex flex-col items-center gap-2 md:inset-x-auto md:right-4 md:bottom-4 md:items-end"
      >
        {items.map((item) => (
          <ToastCard key={item.id} item={item} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const ICONS = { success: CircleCheck, info: Info, error: CircleAlert } as const;

/** One toast: a kind icon, the message and a dismiss button, with the auto-dismiss timer. */
function ToastCard({ item, onDismiss }: { item: ToastItem; onDismiss: (id: number) => void }) {
  const { t } = useTranslation();
  // Hover and focus each pause the timer; it runs only while neither is on the toast.
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const paused = hovered || focused;
  const remaining = useRef(TOAST_MS);
  const startedAt = useRef(0);
  const Icon = ICONS[item.kind];

  useEffect(() => {
    if (item.kind === "error" || paused) return;
    startedAt.current = Date.now();
    const timer = setTimeout(() => onDismiss(item.id), remaining.current);
    return () => {
      clearTimeout(timer);
      remaining.current -= Date.now() - startedAt.current;
    };
  }, [item.id, item.kind, paused, onDismiss]);

  return (
    <div
      role={item.kind === "error" ? "alert" : undefined}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      className={cn(
        "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border bg-popover p-3 text-sm text-popover-foreground shadow-md",
        item.kind === "error" && "border-destructive",
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn(
          "mt-0.5 size-4 shrink-0",
          item.kind === "success" && "text-success",
          item.kind === "info" && "text-primary",
          item.kind === "error" && "text-destructive",
        )}
      />
      <p className="flex-1">{item.message}</p>
      <button
        type="button"
        aria-label={t("toast.dismiss")}
        onClick={() => onDismiss(item.id)}
        className="-m-1 inline-flex size-8 shrink-0 items-center justify-center rounded-md outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring pointer-coarse:size-11"
      >
        <X aria-hidden="true" className="size-4" />
      </button>
    </div>
  );
}
