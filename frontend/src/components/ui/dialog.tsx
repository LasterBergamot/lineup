import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * A modal dialog on the native `<dialog>` element: `showModal()` gives the focus trap, the Esc key,
 * the inert page behind it and `aria-modal` for free, so there is no library. While `open` is true
 * the dialog is shown and the `children` are mounted (a closed dialog renders none, so a heavy
 * child such as the PDF viewer only exists while it is on screen). The title labels the dialog
 * (`aria-labelledby`), the optional `description` describes it (`aria-describedby`), and the
 * close button, Esc and a click on the scrim all call `onClose`: the owner of the state closes it.
 * Focus goes back to whatever opened it. For a destructive row action keep using `ConfirmButton`.
 */
export function Dialog({
  open,
  onClose,
  title,
  description,
  closeLabel,
  className,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  /** Accessible name of the close button, translated by the caller. */
  closeLabel: string;
  className?: string;
  children?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = ref.current!;
    if (open && !dialog.open) {
      opener.current = document.activeElement;
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
      (opener.current as HTMLElement | null)?.focus();
    }
  }, [open]);

  // A dialog that is unmounted while open (its owner stops rendering it, as `PreviewPanel` does)
  // never runs the branch above, and removing a modal <dialog> does not reliably return focus.
  useEffect(
    () => () => {
      (opener.current as HTMLElement | null)?.focus();
    },
    [],
  );

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      // Esc closes the dialog natively and fires `close`; a close we caused (`open` already
      // false) must not call `onClose` a second time.
      onClose={() => {
        if (open) onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className={cn(
        "m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border bg-popover p-0 text-popover-foreground shadow-lg backdrop:bg-overlay",
        className,
      )}
    >
      {open && (
        <div className="flex max-h-full flex-col gap-3 p-6">
          <div className="flex items-start justify-between gap-3">
            <h2 id={titleId} className="text-lg font-semibold">
              {title}
            </h2>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={closeLabel}
              onClick={onClose}
            >
              <X />
            </Button>
          </div>
          {description && (
            <p id={descriptionId} className="text-sm text-muted-foreground">
              {description}
            </p>
          )}
          {children}
        </div>
      )}
    </dialog>
  );
}
