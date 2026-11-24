import type { ReactNode } from "react";
import { UnsavedChangesContext } from "@/lib/unsaved-changes";

/**
 * Records what forms report to the unsaved-changes guard, without a router: wrap the form in
 * `Wrapper`, then `isDirty()` says whether any form currently reports unsaved changes.
 */
export function unsavedProbe() {
  const state = new Map<string, boolean>();
  const report = vi.fn((id: string, dirty: boolean) => state.set(id, dirty));
  return {
    report,
    isDirty: () => [...state.values()].some(Boolean),
    Wrapper: ({ children }: { children: ReactNode }) => (
      <UnsavedChangesContext.Provider value={report}>{children}</UnsavedChangesContext.Provider>
    ),
  };
}
