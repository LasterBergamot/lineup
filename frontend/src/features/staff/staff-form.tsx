import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm, useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { ApiError, describeError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Combobox } from "@/components/ui/combobox";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import type { Player } from "@/features/players/api";
import { ROLE_LABELS, STAFF_ROLES, type Staff } from "@/features/staff/api";
import { EMPTY_STAFF, staffFormSchema, type StaffFormValues } from "@/features/staff/schema";
import { sortByName } from "@/lib/sort-by-name";
import { useUnsavedChangesGuard } from "@/lib/unsaved-changes";

/** API body field -> form field, for mapping a server 422 onto the right input. */
const SERVER_FIELDS = {
  role: "role",
  name: "name",
  source_player_id: "playerId",
  is_default: "isDefault",
} as const;

/**
 * The add and the edit staff form: the role, a roster player to copy the name from (or "Type in
 * by hand") and the name, plus "default for this role". Picking a player copies their current
 * name into the name box, which is then read-only (like a roster pick in the lineup creator);
 * choosing "Type in by hand" again frees it. The name is a copy and does not follow the player.
 *
 * It owns its mutation (`save`), so each form shows its own pending state and errors; `onSettled`
 * runs after it either way, which is where the caller reloads the list (a 404 usually means
 * another member deleted the entry or the player meanwhile). A server 422 is shown on the field
 * it names, a 409 (another member set a different default for the role at the same moment) as
 * its own sentence, and any other failure as a generic one. The values live in this form's state only:
 * never in storage, a query key or a log. Unsaved input is guarded (`useUnsavedChangesGuard`).
 */
export function StaffForm({
  label,
  submitLabel,
  defaultValues = EMPTY_STAFF,
  roster,
  save,
  onSettled,
  onSuccess,
  onCancel,
  resetOnSuccess = false,
}: {
  /** Accessible name of the form, so several forms on one page can be told apart. */
  label: string;
  submitLabel: string;
  defaultValues?: StaffFormValues;
  /** The team's players, to pick a staff member from. */
  roster: readonly Player[];
  save: (values: StaffFormValues) => Promise<Staff>;
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
    setValue,
    reset,
    control,
    formState: { errors, isDirty },
  } = useForm<StaffFormValues>({ resolver: zodResolver(staffFormSchema), defaultValues });
  useUnsavedChangesGuard(isDirty);
  const playerId = useWatch({ control, name: "playerId" });

  const mutation = useMutation({
    mutationFn: save,
    onSuccess: (_saved, values) => {
      reset(resetOnSuccess ? { ...EMPTY_STAFF, role: values.role } : values);
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

  /** Copies the picked player's name in (or keeps the typed name for "Type in by hand"). */
  function pickPlayer(id: string) {
    setValue("playerId", id, { shouldDirty: true });
    const player = roster.find((p) => p.id === id);
    if (player) setValue("name", player.name, { shouldDirty: true, shouldValidate: true });
  }

  const options = sortByName(roster).map((player) => ({
    value: player.id,
    label: player.name,
    hint: player.nssz_number,
  }));

  return (
    <form
      noValidate
      aria-label={label}
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex flex-col gap-3"
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label={t("staff.role")} error={errors.role?.message}>
          {(props) => (
            <Select {...props} {...register("role")}>
              {STAFF_ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(ROLE_LABELS[role])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("creator.rosterPlayer")} error={errors.playerId?.message}>
          {(props) => (
            <Combobox
              {...props}
              value={playerId}
              onChange={pickPlayer}
              emptyLabel={t("creator.typedIn")}
              noMatchesLabel={t("creator.noPlayerMatches")}
              options={options}
            />
          )}
        </Field>
        <Field label={t("fields.name")} error={errors.name?.message}>
          {(props) => (
            <Input
              {...props}
              autoComplete="off"
              readOnly={Boolean(playerId)}
              {...register("name")}
            />
          )}
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm pointer-coarse:min-h-11">
        <input type="checkbox" className="size-4 accent-primary" {...register("isDefault")} />
        {t("staff.isDefault")}
      </label>
      {mutation.isError && !shownOnFields && (
        <p role="alert" className="text-sm text-destructive">
          {mutation.error instanceof ApiError && mutation.error.status === 409
            ? t("staff.conflict")
            : describeError(mutation.error, t)}
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
