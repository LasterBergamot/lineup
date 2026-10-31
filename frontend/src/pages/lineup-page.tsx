import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { LineupCreator } from "@/features/creator/lineup-creator";
import { isSavedLineup, valuesFromSaved } from "@/features/creator/resolve";
import { LineupForm } from "@/features/lineup/lineup-form";
import { listPlayers, playersKey } from "@/features/players/api";
import { useTeams } from "@/features/teams/context";

/**
 * Make a lineup. The creator (default) builds it from the current team's roster, previews it and
 * saves it; "Quick sheet" is the one-off form for a lineup nobody needs to keep. When the Saved
 * page sends a lineup to clone (`location.state.cloneFrom`), the creator starts from it.
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
  if (!current) return null;
  const cloneFrom = (location.state as { cloneFrom?: unknown } | null)?.cloneFrom;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("lineup.title")}</h1>
        <p className="text-muted-foreground">
          {t(quick ? "lineup.description" : "creator.description", { team: current.name })}
        </p>
      </div>
      <div className="flex gap-2" role="group" aria-label={t("creator.modes")}>
        <Button
          type="button"
          size="sm"
          variant={quick ? "outline" : "default"}
          aria-pressed={!quick}
          onClick={() => setQuick(false)}
        >
          {t("creator.modeCreator")}
        </Button>
        <Button
          type="button"
          size="sm"
          variant={quick ? "default" : "outline"}
          aria-pressed={quick}
          onClick={() => setQuick(true)}
        >
          {t("creator.modeQuick")}
        </Button>
      </div>
      {quick ? (
        <LineupForm />
      ) : (
        <QueryBoundary
          query={roster}
          skeleton={
            <div className="flex flex-col gap-6">
              <Skeleton className="h-56 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          }
        >
          {(players) => (
            <LineupCreator
              key={isSavedLineup(cloneFrom) ? cloneFrom.id : "new"}
              team={current}
              roster={players}
              initialValues={isSavedLineup(cloneFrom) ? valuesFromSaved(cloneFrom, players) : undefined}
            />
          )}
        </QueryBoundary>
      )}
    </div>
  );
}
