import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Eraser } from "lucide-react";
import { useForm, useWatch, type FieldPath } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { describeError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { saveFile } from "@/features/lineup/download";
import { generateLineup, type LineupFormat } from "@/features/lineup/generate";
import { filledRows, isEmptyRow, rowPath } from "@/features/lineup/cap-rows";
import {
  CAP_COLOURS,
  emptyQuickSheetValues,
  lineupSchema,
  MAX_PLAYERS,
  toQuickSheetRequest,
  type LineupFormValues,
} from "@/features/lineup/schema";
import { translateError } from "@/i18n/error-key";
import { useAfterDelay } from "@/lib/use-after-delay";
import { useUnsavedChangesGuard } from "@/lib/unsaved-changes";
import { cn } from "@/lib/utils";

/** How long a PDF may take before we explain that the first one after a break is slower. */
export const SLOW_PDF_NOTICE_MS = 5000;

/** Sample values for the placeholders: real Hungarian data formats, the same in both languages. */
const EXAMPLES = {
  match: "SZVTK - Csongrád",
  division: "OB II.",
  team: "SZVTK",
  date: "2024. 12. 21.",
};

const STAFF_FIELDS = [
  ["coach", "fields.coach"],
  ["doctor", "fields.doctor"],
  ["assistant_coach", "fields.assistantCoach"],
  ["team_leader", "fields.teamLeader"],
  ["ball_thrower", "fields.ballThrower"],
] as const;

/**
 * The one-off lineup form: fill in the match, the staff and the players in 15 fixed cap rows (empty
 * rows are left out), then download the sheet as PDF or DOCX. Nothing is saved anywhere: the values live in this component's memory
 * only (no localStorage drafts), because they include players' names and NSSZ numbers.
 */
export function LineupForm() {
  const { t } = useTranslation();
  const {
    register,
    handleSubmit,
    control,
    setError,
    setValue,
    clearErrors,
    reset,
    formState: { errors, isDirty },
  } = useForm<LineupFormValues>({
    resolver: zodResolver(lineupSchema),
    defaultValues: emptyQuickSheetValues(),
  });
  const players = useWatch({ control, name: "players" });
  // Nothing is saved here, so a finished download counts as done: it makes the downloaded values
  // the new baseline (the guard turns off until the next edit).
  useUnsavedChangesGuard(isDirty);

  const generate = useMutation({
    mutationFn: ({ values, format }: { values: LineupFormValues; format: LineupFormat }) =>
      generateLineup(toQuickSheetRequest(values), format),
    onSuccess: (file, { values }) => {
      saveFile(file);
      reset(values);
    },
    onError: (error, { values }) => {
      for (const { path, message } of fieldErrors(error)) {
        const target = path === "players" ? "players.root" : rowPath(path, values.players);
        setError(target as FieldPath<LineupFormValues>, { type: "server", message });
      }
    },
  });

  const pendingFormat = generate.isPending ? generate.variables.format : undefined;
  const showSlowNotice = useAfterDelay(pendingFormat === "pdf", SLOW_PDF_NOTICE_MS);
  const rejectedByServer = generate.isError && fieldErrors(generate.error).length > 0;

  const submitAs = (format: LineupFormat) =>
    handleSubmit((values) => generate.mutate({ values, format }));

  /** Empties one cap row (and its errors); an empty row is left out of the sheet. */
  function clearRow(index: number) {
    setValue(`players.${index}.name`, "", { shouldDirty: true });
    setValue(`players.${index}.nssz_number`, "", { shouldDirty: true });
    clearErrors(`players.${index}`);
  }

  const playersError = errors.players?.root?.message ?? errors.players?.message;

  return (
    <form onSubmit={submitAs("pdf")} noValidate className="flex flex-col gap-6" autoComplete="off">
      <Card>
        <CardHeader>
          <CardTitle>{t("lineup.sections.match")}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label={t("fields.match")} error={errors.match?.message}>
            {(props) => <Input {...props} placeholder={EXAMPLES.match} {...register("match")} />}
          </Field>
          <Field label={t("fields.division")} error={errors.division?.message}>
            {(props) => (
              <Input {...props} placeholder={EXAMPLES.division} {...register("division")} />
            )}
          </Field>
          <Field label={t("fields.teamName")} error={errors.team_name?.message}>
            {(props) => <Input {...props} placeholder={EXAMPLES.team} {...register("team_name")} />}
          </Field>
          <Field label={t("fields.capColour")} error={errors.cap?.message}>
            {(props) => (
              <Select {...props} {...register("cap")}>
                {CAP_COLOURS.map((colour) => (
                  <option key={colour} value={colour}>
                    {t(`lineup.caps.${colour}`)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
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
          {STAFF_FIELDS.map(([name, labelKey]) => (
            <Field key={name} label={t(labelKey)} error={errors[name]?.message}>
              {(props) => <Input {...props} {...register(name)} />}
            </Field>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {t("lineup.sections.players")}{" "}
            <span className="text-sm font-normal text-muted-foreground">
              {t("lineup.playerCount", { count: filledRows(players).length, max: MAX_PLAYERS })}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="@container flex flex-col gap-4 @2xl:gap-2">
          {playersError && (
            <p role="alert" className="text-sm text-destructive">
              {translateError(playersError, t)}
            </p>
          )}
          {players.map((row, index) => {
            const rowErrors = errors.players?.[index];
            // On a wide card the rows line up like a table: only the first shows its labels.
            const compact = index > 0;
            return (
              <div
                key={row.cap_number}
                role="group"
                aria-label={t("lineup.capRow", { number: row.cap_number })}
                className={cn(
                  "grid grid-cols-[2.75rem_minmax(0,1fr)_auto] items-start gap-x-3 gap-y-2 border-b pb-4 last:border-b-0 last:pb-0",
                  "@2xl:grid-cols-[2.75rem_minmax(0,1fr)_14rem_auto] @2xl:border-b-0 @2xl:pb-0",
                  compact && "@2xl:[&_label]:sr-only",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "row-span-2 mt-[1.625rem] flex h-10 items-center justify-center rounded-md bg-muted text-sm font-semibold tabular-nums pointer-coarse:h-11 @2xl:row-span-1",
                    compact && "@2xl:mt-0",
                  )}
                >
                  {row.cap_number}
                </span>
                <Field label={t("fields.name")} error={rowErrors?.name?.message}>
                  {(props) => <Input {...props} {...register(`players.${index}.name`)} />}
                </Field>
                <Field
                  label={t("fields.nsszNumber")}
                  error={rowErrors?.nssz_number?.message}
                  className="col-start-2 @2xl:col-start-auto"
                >
                  {(props) => <Input {...props} {...register(`players.${index}.nssz_number`)} />}
                </Field>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "col-start-3 row-start-1 mt-[1.625rem] @2xl:col-start-auto @2xl:row-start-auto",
                    compact && "@2xl:mt-0",
                  )}
                  aria-label={t("lineup.clearRow", { number: row.cap_number })}
                  onClick={() => clearRow(index)}
                  disabled={isEmptyRow(row)}
                >
                  <Eraser />
                </Button>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <div className="flex flex-col gap-3">
        {generate.isError && (
          <p
            role="alert"
            className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
          >
            {rejectedByServer ? t("errors.serverRejectedFields") : describeError(generate.error, t)}
          </p>
        )}
        {showSlowNotice && (
          <p role="status" className="text-sm text-muted-foreground">
            {t("lineup.slowPdf")}
          </p>
        )}
        {generate.isSuccess && (
          <p role="status" className="text-sm text-muted-foreground">
            {t("lineup.downloaded", { filename: generate.data.filename })}
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={pendingFormat === "pdf"} disabled={generate.isPending}>
            {t("lineup.downloadPdf")}
          </Button>
          <Button
            type="button"
            variant="outline"
            loading={pendingFormat === "docx"}
            disabled={generate.isPending}
            onClick={submitAs("docx")}
          >
            {t("lineup.downloadDocx")}
          </Button>
        </div>
      </div>
    </form>
  );
}
