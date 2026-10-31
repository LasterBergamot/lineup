import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { ApiError, describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { saveFile } from "@/features/lineup/download";
import { generateSavedLineup, type LineupFormat } from "@/features/lineup/generate";
import { PdfViewer } from "@/features/preview/pdf-viewer";
import { PreviewPanel } from "@/features/preview/preview-panel";
import {
  deleteSavedLineup,
  listSavedLineups,
  savedLineupsKey,
  savedPreviewKey,
  type SavedLineup,
} from "@/features/saved/api";
import type { Team } from "@/features/teams/api";
import { cn } from "@/lib/utils";
import { useAfterDelay } from "@/lib/use-after-delay";

/** How long the pointer must rest on a row before its preview loads (hover intent, desktop). */
export const HOVER_INTENT_MS = 300;

/** How long a PDF may take before we explain that the first one after a break is slower. */
export const SLOW_PDF_NOTICE_MS = 5000;

/** The download buttons of every row, in this order. */
const FORMATS: readonly LineupFormat[] = ["pdf", "docx"];

/** A failure that means "this lineup no longer exists for you" rather than a broken request. */
const isGone = (error: unknown) => error instanceof ApiError && error.status === 404;

/**
 * The current team's saved lineups, newest first, each with Preview, PDF/DOCX download, "Clone to
 * new match" and Delete. Previews are the PDF of the frozen snapshot: they load on a tap of the
 * Preview button, or after the pointer rests on a row for {@link HOVER_INTENT_MS} (so moving the
 * mouse across the list does not start a PDF for every row; each one counts against the generate
 * rate limit). A preview is cached in memory per lineup for as long as the page is open
 * (`staleTime: Infinity`: snapshots never change) and never stored or given a URL. Clone opens the
 * Lineup page with only the lineup's id in the router state (`cloneFromId`); the page fetches the
 * lineup itself and pre-fills a new one from it. Router state is kept in the browser's tab history,
 * so it must never carry names or NSSZ numbers. A 404 means another member deleted the lineup meanwhile: the list reloads
 * and says so.
 */
export function SavedLineups({ team }: { team: Team }) {
  const { t } = useTranslation();
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const listKey = savedLineupsKey(userId, team.id);
  const [selected, setSelected] = useState<SavedLineup | null>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const lineups = useQuery({ queryKey: listKey, queryFn: () => listSavedLineups(team.id) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: listKey, exact: true });

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

  useEffect(() => () => clearTimeout(hoverTimer.current), []);

  function hoverStart(lineup: SavedLineup) {
    clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(() => setSelected(lineup), HOVER_INTENT_MS);
  }

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
      {(rows) =>
        rows.length === 0 ? (
          <p className="border bg-card p-4 text-sm text-muted-foreground">
            {t("savedLineups.empty")}
          </p>
        ) : (
          <ul
            aria-label={t("savedLineups.listLabel", { team: team.name })}
            className="flex flex-col divide-y border bg-card"
          >
            {rows.map((lineup) => (
              <li
                key={lineup.id}
                className={cn(
                  "flex flex-col gap-3 border-l-4 border-l-transparent p-4 md:flex-row md:items-center md:justify-between",
                  selected?.id === lineup.id && "border-l-primary bg-accent",
                )}
                aria-current={selected?.id === lineup.id ? "true" : undefined}
                onMouseEnter={() => hoverStart(lineup)}
                onMouseLeave={() => clearTimeout(hoverTimer.current)}
              >
                <div className="flex flex-col gap-1">
                  <p className="font-medium">{lineup.match_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {t("savedLineups.details", {
                      date: lineup.date,
                      division: lineup.division,
                      cap: t(`lineup.caps.${lineup.cap as "Fehér" | "Kék"}`, {
                        defaultValue: lineup.cap,
                      }),
                      opponent: lineup.opponent_name,
                    })}
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
        )
      }
    </QueryBoundary>
  );

  return (
    <div className="flex flex-col gap-4">
      {failure && (
        <p role="alert" className="border border-destructive p-3 text-sm text-destructive">
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
          >
            {preview.isError ? (
              <p role="alert" className="border border-destructive p-3 text-sm text-destructive">
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
