import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { QueryBoundary } from "@/components/query-boundary";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { LineupCreator } from "@/features/creator/lineup-creator";
import { getSavedLineup, type SavedLineup } from "@/features/creator/api";
import { valuesForEdit, valuesFromSaved } from "@/features/creator/resolve";
import { LineupForm } from "@/features/lineup/lineup-form";
import { listPlayers, playersKey, type Player } from "@/features/players/api";
import { listStaff, staffKey, type Staff } from "@/features/staff/api";
import { useTeams } from "@/features/teams/context";

/**
 * Make a lineup. The creator (default) builds it from the current team's roster, previews it and
 * saves it; "Quick sheet" is the one-off form for a lineup nobody needs to keep. When the Saved
 * page sends the id of a lineup to clone (`location.state.cloneFromId`), the page fetches it and the
 * creator starts from it. With `location.state.editFromId` (#290) the page edits that lineup in
 * place instead: the heading names it, there is no Quick sheet, and the creator saves changes to
 * it; after a 409 its "load the latest version" refetches the lineup and mounts a fresh creator. Both modes stay mounted and the inactive one is hidden, so switching
 * keeps what was typed in either (the values live in component state only, never in storage).
 * Only the id travels in the router state: the lineup itself holds players' names and NSSZ
 * numbers, which must not end up in the browser's history entries. Both forms wait for the team's
 * staff (#289), since a new lineup starts with each role's default and those are read only once,
 * when the form mounts.
 */
export function LineupPage() {
  const { t } = useTranslation();
  const { current } = useTeams();
  const { userId } = useAuth();
  const location = useLocation();
  const [quick, setQuick] = useState(false);
  const roster = useQuery({
    queryKey: playersKey(userId, current?.id ?? ""),
    queryFn: () => listPlayers(current!.id),
    enabled: Boolean(current),
  });
  const staff = useQuery({
    queryKey: staffKey(userId, current?.id ?? ""),
    queryFn: () => listStaff(current!.id),
    enabled: Boolean(current),
  });
  const state = location.state as { cloneFromId?: unknown; editFromId?: unknown } | null;
  const editId = typeof state?.editFromId === "string" ? state.editFromId : undefined;
  const cloneId =
    editId === undefined && typeof state?.cloneFromId === "string" ? state.cloneFromId : undefined;
  const sourceId = editId ?? cloneId;
  const source = useQuery({
    queryKey: ["saved", userId, current?.id ?? "", editId ? "edit" : "clone", sourceId ?? ""],
    queryFn: () => getSavedLineup(sourceId!),
    enabled: Boolean(current) && sourceId !== undefined,
  });
  // Bumped by "load the latest version": a new key mounts a fresh creator from the refetched data.
  const [reloads, setReloads] = useState(0);
  if (!current) return null;

  /** Roster, then staff, then (for a clone or an edit) the lineup, each with its own boundary. */
  const withData = (
    render: (players: Player[], entries: Staff[], saved: SavedLineup | undefined) => ReactNode,
  ) => (
    <QueryBoundary query={roster} skeleton={<CreatorSkeleton />}>
      {(players) => (
        <QueryBoundary query={staff} skeleton={<CreatorSkeleton />}>
          {(entries) =>
            sourceId === undefined ? (
              render(players, entries, undefined)
            ) : (
              <QueryBoundary query={source} skeleton={<CreatorSkeleton />}>
                {(saved) => render(players, entries, saved)}
              </QueryBoundary>
            )
          }
        </QueryBoundary>
      )}
    </QueryBoundary>
  );

  if (editId !== undefined) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            {source.data
              ? t("creator.editTitle", { match: source.data.match_name })
              : t("creator.editTitleLoading")}
          </h1>
          <p className="text-muted-foreground">{t("creator.editDescription")}</p>
        </div>
        {withData((players, entries, saved) => (
          <LineupCreator
            key={`${saved!.id}:${reloads}`}
            team={current}
            roster={players}
            staff={entries}
            initialValues={valuesForEdit(saved!, players)}
            edit={{
              lineup: saved!,
              onReload: () => void source.refetch().then(() => setReloads((n) => n + 1)),
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("lineup.title")}</h1>
        <p className="text-muted-foreground">
          {t(quick ? "lineup.description" : "creator.description", { team: current.name })}
        </p>
      </div>
      <Tabs
        id="lineup-mode"
        label={t("creator.modes")}
        value={quick ? "quick" : "creator"}
        onChange={(mode) => setQuick(mode === "quick")}
        options={[
          { value: "creator", label: t("creator.modeCreator") },
          { value: "quick", label: t("creator.modeQuick") },
        ]}
      />
      <div
        role="tabpanel"
        id="lineup-mode-panel"
        aria-labelledby={quick ? "lineup-mode-quick" : "lineup-mode-creator"}
        className="flex flex-col gap-6"
      >
        {/* Both modes stay mounted and the inactive one is hidden, so a switch never drops what was
            typed (#302) and both forms keep reporting their dirty flag to the unsaved-changes guard.
            The `hidden` goes on a wrapper without a display class: `flex` would override it. */}
        <div hidden={quick}>
          {withData((players, entries, saved) =>
            saved === undefined ? (
              <LineupCreator key="new" team={current} roster={players} staff={entries} />
            ) : (
              <LineupCreator
                key={saved.id}
                team={current}
                roster={players}
                staff={entries}
                initialValues={valuesFromSaved(saved, players)}
              />
            ),
          )}
        </div>
        <div hidden={!quick}>
          <QueryBoundary query={staff} skeleton={<CreatorSkeleton />}>
            {(entries) => <LineupForm staff={entries} />}
          </QueryBoundary>
        </div>
      </div>
    </div>
  );
}

/** Placeholder in the shape of the creator while the roster (or a lineup to clone) loads. */
function CreatorSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
