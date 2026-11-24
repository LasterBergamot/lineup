import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { ApiError, describeError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import type { Player } from "@/features/players/api";
import { playerFormSchema, type PlayerFormValues } from "@/features/players/schema";
import { useUnsavedChangesGuard } from "@/lib/unsaved-changes";

/** API body field -> form field, for mapping a server 422 onto the right input. */
const SERVER_FIELDS = { name: "name", nssz_number: "nsszNumber" } as const;

/** A name compared the way a person would: ignoring case and surrounding or doubled spaces. */
const nameKey = (name: string) => name.trim().replace(/\s+/g, " ").toLowerCase();

/**
 * The add and the edit player form (name + NSSZ number, nothing more: data minimisation). It owns
 * its mutation so each form shows its own pending state and errors: `save` makes the request and
 * `onSettled` runs after it either way, which is where the caller refreshes the roster (a 404
 * means someone else deleted the player, so the list must be reloaded then too). A server 422 is
 * shown on the field it names, a 409 (the NSSZ number is already on the roster) on the NSSZ
 * field in our own translated words; any other failure as a generic sentence. With
 * `resetOnSuccess` the fields empty after a save, ready for the next player.
 *
 * A name that another player on the roster already has is allowed (namesakes exist), but the
 * first submit only shows a warning and turns the button into "save anyway"; the second one
 * saves. Changing the name takes the warning back. `otherPlayers` is the rest of the roster (not
 * the player being edited); the check runs here, on data the page already loaded.
 *
 * The values live in this form's state only: never in storage, a query key or a log. Unsaved input
 * is guarded (`useUnsavedChangesGuard`).
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
  otherPlayers = [],
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
  /** The rest of the roster, to warn about a repeated name. */
  otherPlayers?: Pick<Player, "name">[];
}) {
  const { t } = useTranslation();
  const {
    register,
    handleSubmit,
    setError,
    reset,
    control,
    formState: { errors, isDirty },
  } = useForm<PlayerFormValues>({ resolver: zodResolver(playerFormSchema), defaultValues });
  // Typed-in but unsaved player data asks before leaving the page; a save that resets the form,
  // or closing the edit form (which unmounts it), turns the guard off.
  useUnsavedChangesGuard(isDirty);

  // The name key the user has already been warned about (and so may now confirm), if any.
  const [warnedKey, setWarnedKey] = useState<string | null>(null);
  const currentKey = nameKey(useWatch({ control, name: "name" }));
  const warning = warnedKey !== null && warnedKey === currentKey;

  const mutation = useMutation({
    mutationFn: save,
    onSuccess: () => {
      if (resetOnSuccess) reset({ name: "", nsszNumber: "" });
      setWarnedKey(null);
      onSuccess?.();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        setError("nsszNumber", { type: "server", message: t("players.nsszTaken") });
      }
      for (const { path, message } of fieldErrors(error)) {
        if (path in SERVER_FIELDS) {
          setError(SERVER_FIELDS[path as keyof typeof SERVER_FIELDS], { type: "server", message });
        }
      }
    },
    onSettled,
  });
  const duplicateNssz = mutation.error instanceof ApiError && mutation.error.status === 409;
  const shownOnFields =
    duplicateNssz || fieldErrors(mutation.error).some(({ path }) => path in SERVER_FIELDS);

  const submit = (values: PlayerFormValues) => {
    const key = nameKey(values.name);
    if (warnedKey !== key && otherPlayers.some((player) => nameKey(player.name) === key)) {
      setWarnedKey(key);
      return;
    }
    mutation.mutate(values);
  };

  return (
    <form
      noValidate
      aria-label={label}
      onSubmit={handleSubmit(submit)}
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
      {warning && (
        <p
          role="status"
          className="rounded-md bg-warning-soft px-3 py-2 text-sm text-warning-soft-foreground"
        >
          {t("players.sameName")}
        </p>
      )}
      {mutation.isError && !shownOnFields && (
        <p role="alert" className="text-sm text-destructive">
          {describeError(mutation.error, t)}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" size="sm" loading={mutation.isPending}>
          {warning ? t("players.saveAnyway") : submitLabel}
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
