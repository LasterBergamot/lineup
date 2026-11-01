import { useRef, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";

export interface TabOption<T extends string> {
  value: T;
  label: string;
}

/**
 * A pill segmented control: one option is selected, the rest are one click away. Two semantics
 * share one look:
 * - `kind="tab"` (default): `role="tablist"` / `role="tab"` / `aria-selected`, for switching between
 *   two views. Give it an `id` and wrap the view in `role="tabpanel"` with `id={`${id}-panel`}`
 *   and `aria-labelledby={`${id}-${value}`}`, so each tab points at its panel.
 * - `kind="radio"`: `role="radiogroup"` / `role="radio"` / `aria-checked`, for choosing a value in
 *   a form (a cap colour, an expiry), where there is no panel to switch.
 *
 * Only the selected option is in the tab order; the arrow keys, Home and End move the selection
 * (the roving-tabindex pattern), and every option is 44 px tall on touch screens.
 */
export function Tabs<T extends string>({
  id,
  label,
  options,
  value,
  onChange,
  kind = "tab",
  className,
}: {
  id: string;
  /** Accessible name of the whole control. */
  label: string;
  options: readonly TabOption<T>[];
  value: T;
  onChange: (value: T) => void;
  kind?: "tab" | "radio";
  className?: string;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const isTab = kind === "tab";

  function onKeyDown(event: KeyboardEvent, index: number) {
    const last = options.length - 1;
    const target =
      event.key === "ArrowRight" || event.key === "ArrowDown"
        ? index === last
          ? 0
          : index + 1
        : event.key === "ArrowLeft" || event.key === "ArrowUp"
          ? index === 0
            ? last
            : index - 1
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (target === null) return;
    event.preventDefault();
    const next = options[target]!;
    onChange(next.value);
    refs.current[next.value]?.focus();
  }

  return (
    <div
      role={isTab ? "tablist" : "radiogroup"}
      aria-label={label}
      className={cn("flex w-fit gap-0.5 rounded-pill bg-muted p-0.5", className)}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            ref={(node) => {
              refs.current[option.value] = node;
            }}
            id={`${id}-${option.value}`}
            type="button"
            role={isTab ? "tab" : "radio"}
            aria-selected={isTab ? selected : undefined}
            aria-checked={isTab ? undefined : selected}
            aria-controls={isTab ? `${id}-panel` : undefined}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(option.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
            className={cn(
              "inline-flex h-8 items-center justify-center rounded-pill px-4 text-sm font-medium transition-colors outline-none pointer-coarse:h-11 focus-visible:ring-2 focus-visible:ring-ring",
              selected
                ? "bg-card text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
