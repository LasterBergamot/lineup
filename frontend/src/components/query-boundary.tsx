import type { ReactNode } from "react";
import { describeError } from "@/api/errors";
import { Button } from "@/components/ui/button";

/** The slice of a TanStack Query result that {@link QueryBoundary} needs. */
interface QueryLike<T> {
  data: T | undefined;
  isPending: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
}

/**
 * One data region's loading / error / content states. Give every list or panel its own
 * boundary with a skeleton in the final shape of the content, so each region fills in as its
 * own data arrives instead of the whole page waiting on the slowest request.
 */
export function QueryBoundary<T>({
  query,
  skeleton,
  children,
}: {
  query: QueryLike<T>;
  skeleton: ReactNode;
  children: (data: T) => ReactNode;
}) {
  if (query.isPending) {
    return (
      <div role="status" aria-busy="true" aria-label="Loading">
        {skeleton}
      </div>
    );
  }
  if (query.isError || query.data === undefined) {
    return (
      <div role="alert" className="flex flex-col items-start gap-3 border bg-card p-4 text-sm">
        <p>{describeError(query.error)}</p>
        <Button size="sm" variant="outline" onClick={() => void query.refetch()}>
          Try again
        </Button>
      </div>
    );
  }
  return <>{children(query.data)}</>;
}
