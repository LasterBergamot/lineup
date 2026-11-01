import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { QueryBoundary } from "@/components/query-boundary";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { LineupCreator } from "@/features/creator/lineup-creator";
import { getSavedLineup } from "@/features/creator/api";
import { valuesFromSaved } from "@/features/creator/resolve";
import { LineupForm } from "@/features/lineup/lineup-form";
import { listPlayers, playersKey } from "@/features/players/api";
import { useTeams } from "@/features/teams/context";

/**
 * Make a lineup. The creator (default) builds it from the current team's roster, previews it and
 * saves it; "Quick sheet" is the one-off form for a lineup nobody needs to keep. When the Saved
 * page sends the id of a lineup to clone (`location.state.cloneFromId`), the page fetches it and the
 * creator starts from it. Only the id travels in the router state: the lineup itself holds players'
 * names and NSSZ numbers, which must not end up in the browser's history entries.
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
  const requested = (location.state as { cloneFromId?: unknown } | null)?.cloneFromId;
  const cloneId = typeof requested === "string" ? requested : undefined;
  const clone = useQuery({
    queryKey: ["saved", userId, current?.id ?? "", "clone", cloneId ?? ""],
    queryFn: () => getSavedLineup(cloneId!),
    enabled: Boolean(current) && cloneId !== undefined,
  });
  if (!current) return null;

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
        {quick ? (
          <LineupForm />
        ) : (
          <QueryBoundary query={roster} skeleton={<CreatorSkeleton />}>
            {(players) =>
              cloneId === undefined ? (
                <LineupCreator key="new" team={current} roster={players} />
              ) : (
                <QueryBoundary query={clone} skeleton={<CreatorSkeleton />}>
                  {(saved) => (
                    <LineupCreator
                      key={saved.id}
                      team={current}
                      roster={players}
                      initialValues={valuesFromSaved(saved, players)}
                    />
                  )}
                </QueryBoundary>
              )
            }
          </QueryBoundary>
        )}
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
