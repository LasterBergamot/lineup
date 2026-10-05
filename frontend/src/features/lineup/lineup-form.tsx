import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useForm, type FieldPath } from "react-hook-form";
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
import { useAfterDelay } from "@/lib/use-after-delay";

/** How long a PDF may take before we explain that the first one after a break is slower. */
export const SLOW_PDF_NOTICE_MS = 5000;

const STAFF_FIELDS = [
  ["coach", "Coach"],
  ["doctor", "Doctor"],
  ["assistant_coach", "Assistant coach"],
  ["team_leader", "Team leader"],
  ["ball_thrower", "Ball thrower"],
] as const;

/**
 * The one-off lineup form: fill in the match, the staff and up to 15 players, then download the
 * sheet as PDF or DOCX. Nothing is saved anywhere: the values live in this component's memory
 * only (no localStorage drafts), because they include players' names and NSSZ numbers.
 */
export function LineupForm() {
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
          <CardTitle>Match</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Match" error={errors.match?.message}>
            {(props) => <Input {...props} placeholder="SZVTK - Csongrád" {...register("match")} />}
          </Field>
          <Field label="Division" error={errors.division?.message}>
            {(props) => <Input {...props} placeholder="OB II." {...register("division")} />}
          </Field>
          <Field label="Team name" error={errors.team_name?.message}>
            {(props) => <Input {...props} placeholder="SZVTK" {...register("team_name")} />}
          </Field>
          <Field label="Cap colour" error={errors.cap?.message}>
            {(props) => (
              <Select {...props} {...register("cap")}>
                {CAP_COLOURS.map((colour) => (
                  <option key={colour} value={colour}>
                    {colour}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label="Date" error={errors.date?.message}>
            {(props) => <Input {...props} placeholder="2024. 12. 21." {...register("date")} />}
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Staff</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          {STAFF_FIELDS.map(([name, label]) => (
            <Field key={name} label={label} error={errors[name]?.message}>
              {(props) => <Input {...props} {...register(name)} />}
            </Field>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between gap-4">
          <CardTitle>
            Players{" "}
            <span className="text-sm font-normal text-muted-foreground">
              ({fields.length} of {MAX_PLAYERS})
            </span>
          </CardTitle>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addPlayer}
            disabled={fields.length >= MAX_PLAYERS}
          >
            <Plus /> Add player
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {playersError && (
            <p role="alert" className="text-sm text-destructive">
              {playersError}
            </p>
          )}
          {fields.map((field, index) => {
            const rowErrors = errors.players?.[index];
            const label = `Player ${index + 1}`;
            return (
              <div
                key={field.id}
                role="group"
                aria-label={label}
                className="grid grid-cols-[5rem_1fr_auto] items-start gap-3 md:grid-cols-[5rem_1fr_14rem_auto]"
              >
                <Field label="Cap no." error={rowErrors?.cap_number?.message}>
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
                <Field label="Name" error={rowErrors?.name?.message}>
                  {(props) => <Input {...props} {...register(`players.${index}.name`)} />}
                </Field>
                <Field
                  label="NSSZ number"
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
                  aria-label={`Remove ${label.toLowerCase()}`}
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
            {rejectedByServer
              ? "The server rejected some of the details. Please check the highlighted fields."
              : describeError(generate.error)}
          </p>
        )}
        {showSlowNotice && (
          <p role="status" className="text-sm text-muted-foreground">
            Generating the PDF — the first one after a break takes a bit longer.
          </p>
        )}
        {generate.isSuccess && (
          <p role="status" className="text-sm text-muted-foreground">
            Downloaded {generate.data.filename}.
          </p>
        )}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={pendingFormat === "pdf"} disabled={generate.isPending}>
            Download PDF
          </Button>
          <Button
            type="button"
            variant="outline"
            loading={pendingFormat === "docx"}
            disabled={generate.isPending}
            onClick={submitAs("docx")}
          >
            Download DOCX
          </Button>
        </div>
      </div>
    </form>
  );
}
