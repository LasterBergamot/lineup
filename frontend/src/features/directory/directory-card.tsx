import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/auth/context";
import { QueryBoundary } from "@/components/query-boundary";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { poolKey, searchPool } from "@/features/directory/api";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** How many teams one search shows; the API allows up to 100. */
const PAGE_SIZE = 20;
/** The API's limit on `search`. */
const MAX_SEARCH_LENGTH = 120;
/** Pause in typing before a search goes out. */
const SEARCH_DELAY_MS = 300;

/**
 * The shared opponent directory: a search over the names of teams that chose to be listed. A
 * blank search shows the first teams alphabetically. Only names are shown (never ids or rosters,
 * which the API does not return anyway). The term lives in component state only: it is not put
 * in the URL, storage or a log. While a new search runs, the previous results stay on screen
 * (`keepPreviousData`) so the list does not flash back to a skeleton on every keystroke.
 */
export function DirectoryCard() {
  const { t } = useTranslation();
  const { userId } = useAuth();
  const [input, setInput] = useState("");
  const search = useDebouncedValue(input.trim(), SEARCH_DELAY_MS);

  const pool = useQuery({
    queryKey: poolKey(userId, search),
    queryFn: () => searchPool(search, PAGE_SIZE),
    placeholderData: keepPreviousData,
    // The directory needs a signed-in caller; waiting also avoids a request keyed by no one.
    enabled: userId !== null,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("directory.title")}</CardTitle>
        <CardDescription>{t("directory.hint")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Field label={t("directory.search")}>
          {(props) => (
            <Input
              {...props}
              type="search"
              autoComplete="off"
              maxLength={MAX_SEARCH_LENGTH}
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
          )}
        </Field>
        <QueryBoundary
          query={pool}
          skeleton={
            <div className="flex flex-col gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          }
        >
          {(teams) =>
            teams.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {search ? t("directory.noMatch") : t("directory.empty")}
              </p>
            ) : (
              <>
                <ul
                  aria-label={t("directory.results")}
                  aria-busy={pool.isPlaceholderData}
                  className="flex flex-col divide-y overflow-hidden rounded-lg border"
                >
                  {teams.map((team) => (
                    <li key={team.id} className="px-3 py-2 text-sm">
                      {team.name}
                    </li>
                  ))}
                </ul>
                {teams.length === PAGE_SIZE && (
                  <p className="text-xs text-muted-foreground">
                    {t("directory.more", { count: PAGE_SIZE })}
                  </p>
                )}
              </>
            )
          }
        </QueryBoundary>
      </CardContent>
    </Card>
  );
}
