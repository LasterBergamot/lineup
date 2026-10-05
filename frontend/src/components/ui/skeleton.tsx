import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

/** Shimmering placeholder in the final shape of the content that is still loading. */
export function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return <div aria-hidden="true" className={cn("animate-pulse bg-muted", className)} {...props} />;
}
