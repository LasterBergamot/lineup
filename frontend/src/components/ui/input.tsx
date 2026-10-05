import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const CONTROL =
  "h-10 w-full border border-input bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive";

/** Single-line text input (square, Polaris). Set `aria-invalid` to show the error state. */
export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(CONTROL, className)} {...props} />;
}

/** Native `<select>` styled like {@link Input}; native keeps the mobile picker and a11y for free. */
export function Select({ className, ...props }: ComponentProps<"select">) {
  return <select className={cn(CONTROL, className)} {...props} />;
}
