import { cn } from "@/lib/utils";

/** The product name: a proper noun, the same in every language. */
const APP_NAME = "Lineup";

/**
 * The wordmark shown on every page: "Lineup" in bold with an amber dot on the baseline. 22px in
 * the app chrome (`md`, the default), 36px on the sign-in page (`lg`). The dot is decorative and
 * not a text node, so the accessible name and `getByText("Lineup")` stay "Lineup". The square
 * "L tile" is only for the favicon and app icons, never shown next to this.
 */
export function Brand({ size = "md" }: { size?: "md" | "lg" }) {
  return (
    <div
      className={cn(
        "font-bold tracking-[-0.035em] text-foreground",
        size === "lg" ? "text-4xl" : "text-[22px]",
      )}
    >
      {APP_NAME}
      <span
        aria-hidden="true"
        className="ml-[0.09em] inline-block size-[0.26em] rounded-full bg-secondary"
      />
    </div>
  );
}
