import { useId, useRef, useState, type KeyboardEvent } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/** One choice of a {@link Combobox}. `hint` (e.g. an id number) is shown and searched too. */
export interface ComboboxOption {
  value: string;
  label: string;
  hint?: string;
  /** Shown but not pickable (e.g. already used in another row). */
  disabled?: boolean;
}

/**
 * Lower-cases and strips accents, so `szucs` finds `Szűcs`. `NFD` splits a letter from its
 * combining marks, which are then dropped.
 */
function fold(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

/**
 * A searchable single choice: the ARIA 1.2 combobox + listbox pattern, hand-written (no new
 * dependency). Type to filter (case and accent insensitive, over the label and the hint), Up/Down
 * to move, Home/End to jump, Enter to pick, Esc to close and drop the typed text, Tab or a click
 * elsewhere to close. The first option is always the "empty" choice (`emptyLabel`, value `""`):
 * it is how a caller keeps a free-text path next to the list. Disabled options stay visible but
 * cannot be picked. The search text lives in component state only. Spread the props `Field`
 * gives (`id`, `aria-*`) onto it like on any input; options keep the order given.
 */
export function Combobox({
  options,
  value,
  onChange,
  emptyLabel,
  noMatchesLabel,
  ...inputProps
}: {
  options: readonly ComboboxOption[];
  /** The picked option's `value`, or `""` for the empty choice. */
  value: string;
  onChange: (value: string) => void;
  /** Text of the first, always-present choice with value `""`. Also the input's placeholder. */
  emptyLabel: string;
  /** Shown in the list when the typed text matches nothing. */
  noMatchesLabel: string;
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState<string | null>(null);
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const selected = options.find((option) => option.value === value);
  const needle = fold((query ?? "").trim());
  const matches = options.filter(
    (option) => !needle || fold(`${option.label} ${option.hint ?? ""}`).includes(needle),
  );
  const shown: ComboboxOption[] = [{ value: "", label: emptyLabel }, ...matches];
  /** Where the list starts when opened: on the current choice (the empty one when none). */
  const current = Math.max(
    shown.findIndex((option) => option.value === value),
    0,
  );
  const optionId = (index: number) => `${listId}-${index}`;

  /** Next enabled index from `from` in `step` direction, staying put at the ends. */
  function move(from: number, step: 1 | -1): number {
    for (let i = from + step; i >= 0 && i < shown.length; i += step) {
      if (!shown[i]!.disabled) return i;
    }
    return from;
  }

  function show(index: number) {
    setActive(index);
    setOpen(true);
    // After the render the active option exists; keep it inside the scrolled list.
    queueMicrotask(() => listRef.current?.children[index]?.scrollIntoView({ block: "nearest" }));
  }

  function close() {
    setOpen(false);
    setQuery(null);
  }

  function pick(index: number) {
    const option = shown[index]!;
    if (option.disabled) return;
    onChange(option.value);
    close();
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        show(open ? move(active, 1) : current);
        break;
      case "ArrowUp":
        event.preventDefault();
        show(open ? move(active, -1) : current);
        break;
      case "Home":
      case "End":
        // Only a list that is open: otherwise they move the text cursor as usual.
        if (open) {
          event.preventDefault();
          show(event.key === "Home" ? move(-1, 1) : move(shown.length, -1));
        }
        break;
      case "Enter":
        // Never submit the form from the picker.
        event.preventDefault();
        if (open) pick(active);
        break;
      case "Escape":
        if (open) {
          // The first Esc only closes the list (not a dialog around it).
          event.preventDefault();
          event.stopPropagation();
          close();
        }
        break;
    }
  }

  return (
    <div className="relative">
      <Input
        {...inputProps}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open ? optionId(active) : undefined}
        autoComplete="off"
        placeholder={emptyLabel}
        value={query ?? selected?.label ?? ""}
        onChange={(event) => {
          const text = event.target.value;
          setQuery(text);
          // Jump to the first real match; with no text, to the current choice's slot.
          const first = fold(text.trim()) ? 1 : 0;
          show(shown.length > first ? first : 0);
        }}
        onKeyDown={onKeyDown}
        onClick={() => (open ? close() : show(current))}
        onBlur={close}
      />
      <div
        hidden={!open}
        className="absolute z-20 mt-1 w-full rounded-md border bg-card text-base shadow-md md:text-sm"
      >
        <ul ref={listRef} id={listId} role="listbox" className="max-h-60 overflow-auto py-1">
          {shown.map((option, index) => (
            <li
              key={option.value || "empty"}
              id={optionId(index)}
              role="option"
              aria-selected={option.value === value}
              aria-disabled={option.disabled || undefined}
              // mousedown would blur the input (closing the list) before the click lands.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => pick(index)}
              className={cn(
                "flex min-h-9 cursor-pointer items-center justify-between gap-3 px-3 py-1.5 pointer-coarse:min-h-11",
                index === active && "bg-muted",
                option.value === value && "font-medium",
                option.disabled && "cursor-not-allowed opacity-50",
                !option.value && "text-muted-foreground",
              )}
            >
              <span>{option.label}</span>
              {option.hint && <span className="text-xs text-muted-foreground">{option.hint}</span>}
            </li>
          ))}
        </ul>
        {needle && matches.length === 0 && (
          <p role="status" className="border-t px-3 py-2 text-muted-foreground">
            {noMatchesLabel}
          </p>
        )}
      </div>
    </div>
  );
}
