import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex h-6 items-center gap-1 rounded-pill px-2.5 text-xs font-medium whitespace-nowrap [&_svg]:size-3 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        neutral: "bg-muted text-foreground",
        primary: "bg-primary-soft text-primary-soft-foreground",
        success: "bg-success-soft text-success-soft-foreground",
        warning: "bg-warning-soft text-warning-soft-foreground",
        danger: "bg-destructive-soft text-destructive-soft-foreground",
        outline: "border border-input text-foreground",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

/**
 * A small pill label: a role, a state or a "Preview" marker. Colour alone never carries the
 * meaning: the children are always a word, and a status badge (`success`, `warning`, `danger`)
 * should pass an `icon` too. The icon is decorative (`aria-hidden`); the word is the accessible name.
 */
export function Badge({
  className,
  variant,
  icon,
  children,
  ...props
}: ComponentProps<"span"> & VariantProps<typeof badgeVariants> & { icon?: ReactNode }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </span>
  );
}
