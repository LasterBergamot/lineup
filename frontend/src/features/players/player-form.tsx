import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { describeError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { Player } from "@/features/players/api";
import { playerFormSchema, type PlayerFormValues } from "@/features/players/schema";

/** API body field -> form field, for mapping a server 422 onto the right input. */
const SERVER_FIELDS = { name: "name", nssz_number: "nsszNumber" } as const;

/**
 * The add and the edit player form (name + NSSZ number, nothing more: data minimisation). It owns
 * its mutation so each form shows its own pending state and errors: `save` makes the request and
 * `onSettled` runs after it either way, which is where the caller refreshes the roster (a 404
 * means someone else deleted the player, so the list must be reloaded then too). A server 422 is
 * shown on the field it names; any other failure as a generic sentence. With `resetOnSuccess`
 * the fields empty after a save, ready for the next player. The values live in this form's state
 * only: never in storage, a query key or a log.
 */
export function PlayerForm({
  label,
  submitLabel,
  defaultValues = { name: "", nsszNumber: "" },
  save,
  onSettled,
  onSuccess,
  onCancel,
  resetOnSuccess = false,
}: {
  /** Accessible name of the form, so several forms on one page can be told apart. */
  label: string;
  submitLabel: string;
  defaultValues?: PlayerFormValues;
  save: (values: PlayerFormValues) => Promise<Player>;
  onSettled?: () => unknown;
  onSuccess?: () => void;
  /** Shows a Cancel button (the inline edit form) that calls this. */
  onCancel?: () => void;
  resetOnSuccess?: boolean;
}) {
  const { t } = useTranslation();
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<PlayerFormValues>({ resolver: zodResolver(playerFormSchema), defaultValues });

  const mutation = useMutation({
    mutationFn: save,
    onSuccess: () => {
      if (resetOnSuccess) reset({ name: "", nsszNumber: "" });
      onSuccess?.();
    },
    onError: (error) => {
      for (const { path, message } of fieldErrors(error)) {
        if (path in SERVER_FIELDS) {
          setError(SERVER_FIELDS[path as keyof typeof SERVER_FIELDS], { type: "server", message });
        }
      }
    },
    onSettled,
  });
  const shownOnFields = fieldErrors(mutation.error).some(({ path }) => path in SERVER_FIELDS);

  return (
    <form
      noValidate
      aria-label={label}
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex flex-col gap-3"
    >
      <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
        <Field label={t("fields.name")} error={errors.name?.message}>
          {(props) => <Input {...props} autoComplete="off" {...register("name")} />}
        </Field>
        <Field label={t("fields.nsszNumber")} error={errors.nsszNumber?.message}>
          {(props) => <Input {...props} autoComplete="off" {...register("nsszNumber")} />}
        </Field>
      </div>
      {mutation.isError && !shownOnFields && (
        <p role="alert" className="text-sm text-destructive">
          {describeError(mutation.error, t)}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" loading={mutation.isPending}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
            {t("common.cancel")}
          </Button>
        )}
      </div>
    </form>
  );
}
