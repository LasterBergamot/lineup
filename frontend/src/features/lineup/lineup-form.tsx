import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useForm, type FieldPath } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { describeError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { saveFile } from "@/features/lineup/download";
import { generateLineup, type LineupFormat } from "@/features/lineup/generate";
import {
  CAP_COLOURS,
  lineupSchema,
  MAX_PLAYERS,
  nextFreeCapNumber,
  type LineupFormValues,
} from "@/features/lineup/schema";
import { translateError } from "@/i18n/error-key";
import { useAfterDelay } from "@/lib/use-after-delay";

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
 * The one-off lineup form: fill in the match, the staff and up to 15 players, then download the
 * sheet as PDF or DOCX. Nothing is saved anywhere: the values live in this component's memory
 * only (no localStorage drafts), because they include players' names and NSSZ numbers.
 */
export function LineupForm() {
  const { t } = useTranslation();
  const {
    register,
    handleSubmit,
    control,
    setError,
    getValues,
    formState: { errors },
  } = useForm<LineupFormValues>({
    resolver: zodResolver(lineupSchema),
    defaultValues: {
      cap: "Fehér",
      players: [{ cap_number: 1, name: "", nssz_number: "" }],
    },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "players" });

  const generate = useMutation({
    mutationFn: ({ values, format }: { values: LineupFormValues; format: LineupFormat }) =>
      generateLineup(values, format),
    onSuccess: (file) => saveFile(file),
    onError: (error) => {
      for (const { path, message } of fieldErrors(error)) {
        const target = path === "players" ? "players.root" : path;
        setError(target as FieldPath<LineupFormValues>, { type: "server", message });
      }
    },
  });

  const pendingFormat = generate.isPending ? generate.variables.format : undefined;
  const showSlowNotice = useAfterDelay(pendingFormat === "pdf", SLOW_PDF_NOTICE_MS);
  const rejectedByServer = generate.isError && fieldErrors(generate.error).length > 0;

  const submitAs = (format: LineupFormat) =>
    handleSubmit((values) => generate.mutate({ values, format }));

  function addPlayer() {
    const next = nextFreeCapNumber(getValues("players").map((p) => p.cap_number));
    if (next !== undefined) append({ cap_number: next, name: "", nssz_number: "" });
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
        <CardContent className="flex flex-col gap-4">
          {playersError && (
            <p role="alert" className="text-sm text-destructive">
              {translateError(playersError, t)}
            </p>
          )}
          {fields.map((field, index) => {
            const rowErrors = errors.players?.[index];
            const label = t("lineup.player", { number: index + 1 });
            return (
              <div
                key={field.id}
                role="group"
                aria-label={label}
                className="grid grid-cols-[5rem_1fr_auto] items-start gap-3 md:grid-cols-[5rem_1fr_14rem_auto]"
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
                <Field label={t("fields.name")} error={rowErrors?.name?.message}>
                  {(props) => <Input {...props} {...register(`players.${index}.name`)} />}
                </Field>
                <Field
                  label={t("fields.nsszNumber")}
                  error={rowErrors?.nssz_number?.message}
                  className="col-span-2 col-start-1 row-start-2 md:col-span-1 md:col-start-auto md:row-start-auto"
                >
                  {(props) => <Input {...props} {...register(`players.${index}.nssz_number`)} />}
                </Field>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-[1.625rem]"
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
        {generate.isError && (
          <p role="alert" className="border border-destructive p-3 text-sm text-destructive">
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
