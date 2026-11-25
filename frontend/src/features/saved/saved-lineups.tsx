import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { ApiError, describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { saveFile } from "@/features/lineup/download";
import { generateSavedLineup, type LineupFormat } from "@/features/lineup/generate";
import { PdfViewer } from "@/features/preview/pdf-viewer";
import { PreviewPanel } from "@/features/preview/preview-panel";
import {
  deleteSavedLineup,
  hasFilters,
  listSavedLineups,
  MAX_LOCATION_LENGTH,
  MAX_OPPONENT_LENGTH,
  NO_FILTERS,
  savedLineupsKey,
  savedListKey,
  savedPreviewKey,
  type SavedFilters,
  type SavedLineup,
} from "@/features/saved/api";
import type { Team } from "@/features/teams/api";
import { cn } from "@/lib/utils";
import { useAfterDelay } from "@/lib/use-after-delay";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** How long a PDF may take before we explain that the first one after a break is slower. */
export const SLOW_PDF_NOTICE_MS = 5000;

/** Pause in typing before the filters go to the server. */
const FILTER_DELAY_MS = 300;

/** The download buttons of every row, in this order. */
const FORMATS: readonly LineupFormat[] = ["pdf", "docx"];

/** A failure that means "this lineup no longer exists for you" rather than a broken request. */
const isGone = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * The current team's saved lineups, newest match first, narrowed by a filter bar (opponent, from
 * and to date, location; all combined, evaluated by the server). Typing is debounced, and while a
 * new search runs the previous rows stay on screen. The filters live in component state and the
 * in-memory query key only: never in the URL, storage or a log. The list is read a page at a time
 * ("Show more"). Each row has Preview, PDF/DOCX download, "Clone to
 * new match" and Delete. Previews are the PDF of the frozen snapshot and load only when the Preview
 * button is pressed. Hovering a row never starts one: each PDF counts against the generate rate
 * limit, and a preview with names should not pop up while the user is just browsing. A preview is
 * cached in memory per lineup for as long as the page is open (`staleTime: Infinity`: snapshots
 * never change) and never stored or given a URL. Clone opens the Lineup page with only the
 * lineup's id in the router state (`cloneFromId`); the page fetches the lineup itself and pre-fills
 * a new one from it. Router state is kept in the browser's tab history, so it must never carry names
 * or NSSZ numbers. A 404 means another member deleted the lineup meanwhile: the list reloads and
 * says so.
 */
export function SavedLineups({ team }: { team: Team }) {
  const { t } = useTranslation();
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [input, setInput] = useState<SavedFilters>(NO_FILTERS);
  const filters = useDebouncedValue(input, FILTER_DELAY_MS);
  const [selected, setSelected] = useState<SavedLineup | null>(null);

  const lineups = useInfiniteQuery({
    queryKey: savedListKey(userId, team.id, filters),
    queryFn: ({ pageParam }) => listSavedLineups(team.id, filters, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((count, page) => count + page.items.length, 0);
      return last.items.length > 0 && loaded < last.total ? loaded : undefined;
    },
    placeholderData: keepPreviousData,
    select: (data) => ({
      items: data.pages.flatMap((page) => page.items),
      total: data.pages[data.pages.length - 1]!.total,
    }),
  });
  // Every filtered list of this team, but not the previews that share the key prefix.
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: [...savedLineupsKey(userId, team.id), "list"] });
  const setFilter = (name: keyof SavedFilters) => (event: ChangeEvent<HTMLInputElement>) =>
    setInput((current) => ({ ...current, [name]: event.target.value }));

  const preview = useQuery({
    queryKey: savedPreviewKey(userId, team.id, selected?.id ?? ""),
    queryFn: async () => (await generateSavedLineup(selected!.id, "pdf")).blob,
    enabled: selected !== null,
    staleTime: Infinity,
    retry: false,
  });

  const download = useMutation({
    mutationFn: ({ id, format }: { id: string; format: LineupFormat }) =>
      generateSavedLineup(id, format),
    onSuccess: (file) => saveFile(file),
    onError: (error) => {
      if (isGone(error)) void refresh();
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteSavedLineup(id),
    onSuccess: (_, id) => {
      if (selected?.id === id) setSelected(null);
    },
    onSettled: refresh,
  });

  const pending = download.isPending ? download.variables : undefined;
  const slowPdf = useAfterDelay(
    preview.isFetching || pending?.format === "pdf",
    SLOW_PDF_NOTICE_MS,
  );
  const failure = download.error ?? remove.error;

  const list = (
    <QueryBoundary
      query={lineups}
      skeleton={
        <div className="flex flex-col gap-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      }
    >
      {({ items: rows, total }) =>
        rows.length === 0 ? (
          <p className="rounded-lg border bg-card p-4 text-sm text-muted-foreground">
            {hasFilters(filters) ? t("savedLineups.filters.noMatch") : t("savedLineups.empty")}
          </p>
        ) : (
          <>
            <ul
              aria-label={t("savedLineups.listLabel", { team: team.name })}
              aria-busy={lineups.isPlaceholderData}
              className="flex flex-col divide-y overflow-hidden rounded-lg border bg-card"
            >
              {rows.map((lineup) => (
                <li
                  key={lineup.id}
                  className={cn(
                    "flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between",
                    selected?.id === lineup.id && "bg-accent",
                  )}
                  aria-current={selected?.id === lineup.id ? "true" : undefined}
                >
                  <div className="flex flex-col gap-1">
                    <p
                      className={cn(
                        "flex flex-wrap items-center gap-2 font-medium",
                        selected?.id === lineup.id && "font-semibold",
                      )}
                    >
                      {lineup.match_name}
                      {selected?.id === lineup.id && (
                        <Badge variant="primary">{t("savedLineups.previewBadge")}</Badge>
                      )}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t("savedLineups.details", {
                        date: lineup.date,
                        division: lineup.division,
                        cap: t(`lineup.caps.${lineup.cap as "Fehér" | "Kék"}`, {
                          defaultValue: lineup.cap,
                        }),
                        opponent: lineup.opponent_name,
                      })}
                      {lineup.location &&
                        ` · ${t("savedLineups.location", { location: lineup.location })}`}
                      {` · ${t("savedLineups.side", {
                        side:
                          lineup.is_home === null
                            ? t("savedLineups.sideUnknown")
                            : t(`creator.homeAway.${lineup.is_home ? "home" : "away"}`),
                      })}`}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      aria-label={t("savedLineups.previewOf", { match: lineup.match_name })}
                      onClick={() => setSelected(lineup)}
                    >
                      {t("savedLineups.preview")}
                    </Button>
                    {FORMATS.map((format) => (
                      <Button
                        key={format}
                        size="sm"
                        variant="outline"
                        aria-label={t(`savedLineups.download.${format}Of`, {
                          match: lineup.match_name,
                        })}
                        loading={pending?.id === lineup.id && pending.format === format}
                        disabled={download.isPending}
                        onClick={() => download.mutate({ id: lineup.id, format })}
                      >
                        {t(`savedLineups.download.${format}`)}
                      </Button>
                    ))}
                    <Button
                      size="sm"
                      variant="outline"
                      aria-label={t("savedLineups.cloneOf", { match: lineup.match_name })}
                      onClick={() => void navigate("/", { state: { cloneFromId: lineup.id } })}
                    >
                      {t("savedLineups.clone")}
                    </Button>
                    <ConfirmButton
                      label={t("savedLineups.delete")}
                      confirmLabel={t("savedLineups.deleteConfirm")}
                      ariaLabel={t("savedLineups.deleteOf", { match: lineup.match_name })}
                      loading={remove.isPending && remove.variables === lineup.id}
                      onConfirm={() => remove.mutate(lineup.id)}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {lineups.hasNextPage && (
              <div className="flex flex-col items-start gap-2">
                <p className="text-sm text-muted-foreground">
                  {t("savedLineups.filters.count", { shown: rows.length, total })}
                </p>
                <Button
                  variant="outline"
                  loading={lineups.isFetchingNextPage}
                  onClick={() => void lineups.fetchNextPage()}
                >
                  {t("savedLineups.filters.more")}
                </Button>
              </div>
            )}
          </>
        )
      }
    </QueryBoundary>
  );

  const filterBar = (
    <div
      role="search"
      aria-label={t("savedLineups.filters.label")}
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      <Field label={t("savedLineups.filters.opponent")}>
        {(props) => (
          <Input
            {...props}
            type="search"
            autoComplete="off"
            maxLength={MAX_OPPONENT_LENGTH}
            value={input.opponent}
            onChange={setFilter("opponent")}
          />
        )}
      </Field>
      <Field label={t("savedLineups.filters.from")}>
        {(props) => (
          <Input
            {...props}
            type="date"
            max={input.dateTo || undefined}
            value={input.dateFrom}
            onChange={setFilter("dateFrom")}
          />
        )}
      </Field>
      <Field label={t("savedLineups.filters.to")}>
        {(props) => (
          <Input
            {...props}
            type="date"
            min={input.dateFrom || undefined}
            value={input.dateTo}
            onChange={setFilter("dateTo")}
          />
        )}
      </Field>
      <Field label={t("savedLineups.filters.location")}>
        {(props) => (
          <Input
            {...props}
            type="search"
            autoComplete="off"
            maxLength={MAX_LOCATION_LENGTH}
            value={input.location}
            onChange={setFilter("location")}
          />
        )}
      </Field>
      {hasFilters(input) && (
        <div className="sm:col-span-2 lg:col-span-4">
          <Button variant="outline" size="sm" onClick={() => setInput(NO_FILTERS)}>
            {t("savedLineups.filters.clear")}
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      {filterBar}
      {failure && (
        <p
          role="alert"
          className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
        >
          {isGone(failure) ? t("savedLineups.gone") : describeError(failure, t)}
        </p>
      )}
      {slowPdf && (
        <p role="status" className="text-sm text-muted-foreground">
          {t("lineup.slowPdf")}
        </p>
      )}
      <div className={selected ? "grid gap-6 lg:grid-cols-[1fr_28rem]" : "grid gap-6"}>
        {list}
        {selected && (
          <PreviewPanel
            title={t("savedLineups.previewTitle", { match: selected.match_name })}
            onClose={() => setSelected(null)}
            file={preview.data}
          >
            {preview.isError ? (
              <p
                role="alert"
                className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
              >
                {isGone(preview.error) ? t("savedLineups.gone") : describeError(preview.error, t)}
              </p>
            ) : preview.data ? (
              <PdfViewer file={preview.data} />
            ) : (
              <div role="status" aria-busy="true" aria-label={t("common.loading")}>
                <Skeleton className="aspect-[1/1.414] w-full" />
              </div>
            )}
          </PreviewPanel>
        )}
      </div>
    </div>
  );
}
