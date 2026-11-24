import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useBlocker, type Location } from "react-router";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { UnsavedChangesContext } from "@/lib/unsaved-changes";

/**
 * A navigation leaves the page's forms behind unless it only re-visits the same address with the
 * same router state (clicking the nav item of the page you are on). A different `state` matters:
 * `/` with `{ cloneFromId }` and plain `/` show different creators.
 */
function leavesPage(current: Location, next: Location) {
  return (
    current.pathname !== next.pathname ||
    current.search !== next.search ||
    current.state !== next.state
  );
}

/**
 * Warns before unsaved form input is lost. Forms report their dirty state through
 * `useUnsavedChangesGuard()`; while any of them is dirty:
 *
 * - an in-app navigation (nav item, link, back button) is held by React Router's `useBlocker` and
 *   a "Discard changes?" dialog asks first: **Stay** cancels the navigation, **Discard** carries it
 *   out (the forms unmount, which clears their flags);
 * - reloading or closing the tab triggers the browser's own `beforeunload` prompt (browsers ignore
 *   custom text there).
 *
 * Mounted once in `AppShell`, inside the data router (`useBlocker` needs one). Signing out is not
 * held: `RequireAuth` unmounts the shell, and with it this blocker, before it redirects.
 */
export function UnsavedChangesGuard({ children }: { children: ReactNode }) {
  const [dirtyForms, setDirtyForms] = useState<ReadonlySet<string>>(() => new Set());
  const report = useCallback((id: string, dirty: boolean) => {
    setDirtyForms((forms) => {
      if (forms.has(id) === dirty) return forms;
      const next = new Set(forms);
      if (dirty) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);
  const dirty = dirtyForms.size > 0;

  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }: { currentLocation: Location; nextLocation: Location }) =>
        dirty && leavesPage(currentLocation, nextLocation),
      [dirty],
    ),
  );

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  return (
    <UnsavedChangesContext.Provider value={report}>
      {children}
      {blocker.state === "blocked" && (
        <DiscardChangesDialog onStay={blocker.reset} onDiscard={blocker.proceed} />
      )}
    </UnsavedChangesContext.Provider>
  );
}

/**
 * The "Discard changes?" question for a held navigation. It exists only while the navigation is
 * held, so its buttons always act on a blocked blocker; Esc, the close button and a scrim click
 * all mean Stay. Unmounting returns focus to whatever was clicked (the nav item).
 */
function DiscardChangesDialog({
  onStay,
  onDiscard,
}: {
  onStay: () => void;
  onDiscard: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Dialog
      open
      onClose={onStay}
      title={t("unsaved.title")}
      description={t("unsaved.description")}
      closeLabel={t("unsaved.close")}
    >
      <div className="flex flex-wrap justify-end gap-3">
        <Button type="button" variant="outline" onClick={onStay}>
          {t("unsaved.stay")}
        </Button>
        <Button type="button" variant="destructive" onClick={onDiscard}>
          {t("unsaved.discard")}
        </Button>
      </div>
    </Dialog>
  );
}
