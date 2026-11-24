import { createContext, useContext, useEffect, useId } from "react";

/**
 * Carries the "this form has unsaved changes" reporter from `UnsavedChangesGuard` to
 * {@link useUnsavedChangesGuard}. The default does nothing, so a form rendered on its own (a
 * component test) works without the guard; in the app every form sits below `AppShell`, which
 * mounts the guard.
 */
export const UnsavedChangesContext = createContext<(id: string, dirty: boolean) => void>(() => {});

/**
 * Tells the page's unsaved-changes guard whether this form holds changes that are not saved yet.
 * While any form on the page reports `true`, leaving through the app's links asks first ("Discard
 * changes?") and reloading or closing the tab shows the browser's own prompt. Pass react-hook-form's
 * `formState.isDirty`, so the guard turns off as soon as a save resets the form; unmounting the
 * form also clears it. Several forms on one page can each call it: one guard (React Router allows a
 * single blocker per router) watches them all.
 *
 * Only the flag travels: the values stay in the form's state, never in storage (they hold names
 * and NSSZ numbers), so there is no draft to restore and the prompt is the only protection.
 */
export function useUnsavedChangesGuard(isDirty: boolean) {
  const report = useContext(UnsavedChangesContext);
  const id = useId();
  useEffect(() => {
    report(id, isDirty);
    return () => report(id, false);
  }, [report, id, isDirty]);
}
