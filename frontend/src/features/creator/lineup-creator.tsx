import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useFieldArray, useForm, useWatch, type FieldPath } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { describeError, fieldErrors } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { createSavedLineup } from "@/features/creator/api";
import { recentOpponentsKey } from "@/features/creator/opponent/api";
import { OpponentCombobox } from "@/features/creator/opponent/opponent-combobox";
import {
  emptyValues,
  formPath,
  toLineupRequest,
  toSavedLineupRequest,
} from "@/features/creator/resolve";
import { creatorSchema, type CreatorValues } from "@/features/creator/schema";
import { saveFile } from "@/features/lineup/download";
import { generateLineup, generateSavedLineup, type LineupFormat } from "@/features/lineup/generate";
import { CAP_COLOURS, MAX_PLAYERS, nextFreeCapNumber } from "@/features/lineup/schema";
import { SLOW_PDF_NOTICE_MS } from "@/features/lineup/lineup-form";
import type { Player } from "@/features/players/api";
import { PdfViewer } from "@/features/preview/pdf-viewer";
import { PreviewPanel } from "@/features/preview/preview-panel";
import type { Team } from "@/features/teams/api";
import { translateError } from "@/i18n/error-key";
import { useAfterDelay } from "@/lib/use-after-delay";

/** Sample values for the placeholders: real Hungarian data formats, the same in both languages. */
const EXAMPLES = { match: "SZVTK - Csongrád", division: "OB II.", date: "2024. 12. 21." };

const DOWNLOADS = [
  ["pdf", "lineup.downloadPdf"],
  ["docx", "lineup.downloadDocx"],
] as const;

const STAFF_FIELDS = [
  ["doctor", "fields.doctor"],
  ["assistant_coach", "fields.assistantCoach"],
  ["team_leader", "fields.teamLeader"],
  ["ball_thrower", "fields.ballThrower"],
] as const;

/**
 * Builds a lineup for `team` from its roster: pick a roster player for each slot (or type one in
 * by hand), choose the opponent from the directory, the team's recent opponents or free text,
 * preview the sheet as a PDF, then save it. A saved lineup can be downloaded right away and is
 * kept in the team's workspace.
 *
 * The form values include players' names and NSSZ numbers: they live in component state only (no
 * storage, no logging), the preview file is a `Blob` that is dropped when the panel closes, and
 * "Save" sends the roster ids so the server freezes the current values itself.
 */
export function LineupCreator({
  team,
  roster,
  initialValues,
}: {
  team: Team;
  roster: readonly Player[];
  initialValues?: CreatorValues;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const [showPreview, setShowPreview] = useState(false);
  const {
    register,
    handleSubmit,
    control,
    setError,
    setValue,
    getValues,
    reset,
    formState: { errors, isDirty },
  } = useForm<CreatorValues>({
    resolver: zodResolver(creatorSchema),
    defaultValues: initialValues ?? emptyValues(),
  });
  const { fields, append, remove } = useFieldArray({ control, name: "players" });
  const players = useWatch({ control, name: "players" });
  const opponent = useWatch({ control, name: "opponent" });
  const cap = useWatch({ control, name: "cap" });

  function showServerErrors(error: unknown) {
    for (const { path, message } of fieldErrors(error)) {
      const target = formPath(path) === "players" ? "players.root" : formPath(path);
      setError(target as FieldPath<CreatorValues>, { type: "server", message });
    }
  }

  // gcTime 0: the preview file holds personal data, so it is dropped as soon as nothing shows it.
  const preview = useMutation({
    gcTime: 0,
    mutationFn: (values: CreatorValues) =>
      generateLineup(toLineupRequest(values, team.name), "pdf"),
    onError: showServerErrors,
  });
  const save = useMutation({
    mutationFn: (values: CreatorValues) => createSavedLineup(toSavedLineupRequest(values, team)),
    onSuccess: async (_saved, values) => {
      // Mark the form as unchanged, so "Saved" stays until the next edit.
      reset(values);
      toast("success", t("creator.savedToast"));
      await queryClient.invalidateQueries({ queryKey: ["saved"] });
      await queryClient.invalidateQueries({ queryKey: recentOpponentsKey(userId, team.id) });
    },
    onError: showServerErrors,
  });
  const download = useMutation({
    mutationFn: async ({ id, format }: { id: string; format: LineupFormat }) =>
      saveFile(await generateSavedLineup(id, format)),
  });

  const showSlowNotice = useAfterDelay(preview.isPending, SLOW_PDF_NOTICE_MS);
  const saved = save.isSuccess && !isDirty ? save.data : undefined;
  const saveRejected = save.isError && fieldErrors(save.error).length > 0;
  const previewRejected = preview.isError && fieldErrors(preview.error).length > 0;

  const openPreview = handleSubmit((values) => {
    setShowPreview(true);
    preview.mutate(values);
  });
  const submitSave = handleSubmit((values) => save.mutate(values));

  function closePreview() {
    setShowPreview(false);
    preview.reset();
  }

  function addPlayer() {
    // The button is disabled at 15 rows, so a free cap number always exists here.
    const next = nextFreeCapNumber(getValues("players").map((p) => p.cap_number))!;
    append({ cap_number: next, playerId: "", name: "", nssz_number: "" });
  }

  /** Copies the picked roster player's name and NSSZ number into the slot (or clears them). */
  function pickPlayer(index: number, playerId: string) {
    const player = roster.find((p) => p.id === playerId);
    setValue(`players.${index}.playerId`, playerId, { shouldDirty: true });
    setValue(`players.${index}.name`, player?.name ?? "", { shouldDirty: true });
    setValue(`players.${index}.nssz_number`, player?.nssz_number ?? "", { shouldDirty: true });
  }

  const playersError = errors.players?.root?.message ?? errors.players?.message;
  const chosen = new Set(players.map((p) => p.playerId).filter(Boolean));

  return (
    <div className={showPreview ? "grid gap-6 lg:grid-cols-[minmax(0,1fr)_28rem]" : undefined}>
      <form
        onSubmit={submitSave}
        noValidate
        autoComplete="off"
        aria-label={t("creator.formLabel")}
        className="flex flex-col gap-6"
      >
        <Card>
          <CardHeader>
            <CardTitle>{t("lineup.sections.match")}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label={t("fields.opponent")} error={errors.opponent?.message}>
              {(props) => (
                <OpponentCombobox
                  {...props}
                  teamId={team.id}
                  value={opponent}
                  onChange={(value, match) => {
                    setValue("opponent", value, { shouldDirty: true });
                    setValue("opponentId", match?.directoryId ?? "", { shouldDirty: true });
                  }}
                />
              )}
            </Field>
            <Field label={t("creator.matchName")} error={errors.match_name?.message}>
              {(props) => (
                <Input {...props} placeholder={EXAMPLES.match} {...register("match_name")} />
              )}
            </Field>
            <Field label={t("fields.division")} error={errors.division?.message}>
              {(props) => (
                <Input {...props} placeholder={EXAMPLES.division} {...register("division")} />
              )}
            </Field>
            <div className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">{t("fields.capColour")}</span>
              <Tabs
                kind="radio"
                id="cap-colour"
                label={t("fields.capColour")}
                value={cap}
                onChange={(colour) => setValue("cap", colour, { shouldDirty: true })}
                options={CAP_COLOURS.map((colour) => ({
                  value: colour,
                  label: t(`lineup.caps.${colour}`),
                }))}
              />
              {errors.cap?.message && (
                <p role="alert" className="text-sm text-destructive">
                  {translateError(errors.cap.message, t)}
                </p>
              )}
            </div>
            <Field label={t("fields.date")} error={errors.date?.message}>
              {(props) => <Input {...props} placeholder={EXAMPLES.date} {...register("date")} />}
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("lineup.sections.staff")}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field label={t("fields.coach")} error={errors.coach?.message}>
              {(props) => <Input {...props} {...register("coach")} />}
            </Field>
            {STAFF_FIELDS.map(([name, labelKey]) => (
              <Field
                key={name}
                label={`${t(labelKey)} (${t("creator.optional")})`}
                error={errors[name]?.message}
              >
                {(props) => <Input {...props} {...register(name)} />}
              </Field>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-4">
            <CardTitle>
              {t("lineup.sections.players")}{" "}
              <span className="text-sm font-normal text-muted-foreground">
                {t("lineup.playerCount", { count: fields.length, max: MAX_PLAYERS })}
              </span>
            </CardTitle>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addPlayer}
              disabled={fields.length >= MAX_PLAYERS}
            >
              <Plus /> {t("lineup.addPlayer")}
            </Button>
          </CardHeader>
          <CardContent className="@container flex flex-col gap-4">
            {roster.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("creator.emptyRoster")}</p>
            )}
            {playersError && (
              <p role="alert" className="text-sm text-destructive">
                {translateError(playersError, t)}
              </p>
            )}
            {fields.map((field, index) => {
              const rowErrors = errors.players?.[index];
              const fromRoster = Boolean(players[index]?.playerId);
              return (
                <div
                  key={field.id}
                  role="group"
                  aria-label={t("lineup.player", { number: index + 1 })}
                  className="grid grid-cols-[5rem_1fr_auto] items-start gap-3 @2xl:grid-cols-[5rem_1fr_1fr_12rem_auto]"
                >
                  <Field label={t("fields.capNo")} error={rowErrors?.cap_number?.message}>
                    {(props) => (
                      <Input
                        {...props}
                        type="number"
                        inputMode="numeric"
                        min={1}
                        max={MAX_PLAYERS}
                        {...register(`players.${index}.cap_number`, { valueAsNumber: true })}
                      />
                    )}
                  </Field>
                  <Field
                    label={t("creator.rosterPlayer")}
                    className="col-span-3 col-start-1 @2xl:col-span-1 @2xl:col-start-auto"
                  >
                    {(props) => (
                      <Select
                        {...props}
                        value={players[index]?.playerId ?? ""}
                        onChange={(event) => pickPlayer(index, event.target.value)}
                      >
                        <option value="">{t("creator.typedIn")}</option>
                        {roster.map((player) => (
                          <option
                            key={player.id}
                            value={player.id}
                            disabled={
                              chosen.has(player.id) && players[index]?.playerId !== player.id
                            }
                          >
                            {player.name}
                          </option>
                        ))}
                      </Select>
                    )}
                  </Field>
                  <Field
                    label={t("fields.name")}
                    error={rowErrors?.name?.message}
                    className="col-span-3 col-start-1 @2xl:col-span-1 @2xl:col-start-auto"
                  >
                    {(props) => (
                      <Input
                        {...props}
                        readOnly={fromRoster}
                        {...register(`players.${index}.name`)}
                      />
                    )}
                  </Field>
                  <Field
                    label={t("fields.nsszNumber")}
                    error={rowErrors?.nssz_number?.message}
                    className="col-span-3 col-start-1 @2xl:col-span-1 @2xl:col-start-auto"
                  >
                    {(props) => (
                      <Input
                        {...props}
                        readOnly={fromRoster}
                        {...register(`players.${index}.nssz_number`)}
                      />
                    )}
                  </Field>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="col-start-3 row-start-1 mt-[1.625rem] self-start @2xl:col-start-auto @2xl:row-start-auto"
                    aria-label={t("lineup.removePlayer", { number: index + 1 })}
                    onClick={() => remove(index)}
                    disabled={fields.length === 1}
                  >
                    <Trash2 />
                  </Button>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3">
          {save.isError && (
            <p
              role="alert"
              className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
            >
              {saveRejected ? t("errors.serverRejectedFields") : describeError(save.error, t)}
            </p>
          )}
          {saved && (
            <div role="status" className="flex flex-col gap-3 rounded-md border p-3 text-sm">
              <p>
                {t("creator.saved")}{" "}
                <Link to="/saved" className="underline">
                  {t("creator.seeSaved")}
                </Link>
              </p>
              {download.isError && (
                <p role="alert" className="text-destructive">
                  {describeError(download.error, t)}
                </p>
              )}
              <div className="flex flex-wrap gap-3">
                {DOWNLOADS.map(([format, labelKey]) => (
                  <Button
                    key={format}
                    type="button"
                    variant="outline"
                    size="sm"
                    loading={download.isPending && download.variables.format === format}
                    disabled={download.isPending}
                    onClick={() => download.mutate({ id: saved.id, format })}
                  >
                    {t(labelKey)}
                  </Button>
                ))}
              </div>
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <Button
              type="submit"
              loading={save.isPending}
              disabled={save.isPending || Boolean(saved)}
            >
              {t("creator.save")}
            </Button>
            <Button
              type="button"
              variant="outline"
              loading={preview.isPending}
              disabled={preview.isPending}
              onClick={openPreview}
            >
              {t("creator.preview")}
            </Button>
          </div>
        </div>
      </form>

      {showPreview && (
        <PreviewPanel title={t("preview.title")} onClose={closePreview}>
          {preview.isPending && (
            <div role="status" aria-busy="true" aria-label={t("common.loading")}>
              <Skeleton className="aspect-[1/1.414] w-full" />
              {showSlowNotice && (
                <p className="mt-3 text-sm text-muted-foreground">{t("lineup.slowPdf")}</p>
              )}
            </div>
          )}
          {preview.isError && (
            <p
              role="alert"
              className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
            >
              {previewRejected ? t("errors.serverRejectedFields") : describeError(preview.error, t)}
            </p>
          )}
          {preview.isSuccess && <PdfViewer file={preview.data.blob} />}
        </PreviewPanel>
      )}
    </div>
  );
}
