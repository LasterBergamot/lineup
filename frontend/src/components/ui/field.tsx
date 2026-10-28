import { useId, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { translateError } from "@/i18n/error-key";
import { cn } from "@/lib/utils";

/**
 * A label, one control and its error message, wired together for screen readers. The control
 * is given as a function so it receives the generated `id` and the `aria-*` props to spread on it.
 * `error` may be an error key made by `errorKey()`; it is translated here, at render time, so a
 * message already on screen follows a language switch.
 */
export function Field({
  label,
  error,
  className,
  children,
}: {
  label: string;
  error?: string;
  className?: string;
  children: (props: {
    id: string;
    "aria-invalid": boolean;
    "aria-describedby": string | undefined;
  }) => ReactNode;
}) {
  const { t } = useTranslation();
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children({
        id,
        "aria-invalid": Boolean(error),
        "aria-describedby": error ? errorId : undefined,
      })}
      {error && (
        <p id={errorId} className="text-sm text-destructive">
          {translateError(error, t)}
        </p>
      )}
    </div>
  );
}
