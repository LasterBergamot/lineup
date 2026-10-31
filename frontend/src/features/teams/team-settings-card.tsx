import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { describeError, fieldErrors } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { teamsKey, updateTeam, type Team } from "@/features/teams/api";
import { teamFormSchema, type TeamFormValues } from "@/features/teams/schema";

/**
 * The owner's settings for a team: its name and whether that name is listed in the shared
 * opponent directory (only the name is ever shared, which the hint says out loud). Renders
 * nothing for a member: callers should mount it for owners only, this is defence in depth (the
 * server answers a member's update with 403 anyway). On save the teams query is refreshed, so
 * the team name shown elsewhere in the app follows.
 */
export function TeamSettingsCard({ team }: { team: Team }) {
  if (team.role !== "owner") return null;
  return <TeamSettingsForm team={team} />;
}

/** The values the form starts from: what the server last said about the team. */
function savedValues(team: Pick<Team, "name" | "is_public">): TeamFormValues {
  return { name: team.name, isPublic: team.is_public };
}

function TeamSettingsForm({ team }: { team: Team }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isDirty },
  } = useForm<TeamFormValues>({
    resolver: zodResolver(teamFormSchema),
    defaultValues: savedValues(team),
  });

  // The prop is the source of truth: when the teams query brings new values (after a save, or
  // another owner's change), they become the form's new baseline, so "nothing changed" holds.
  useEffect(() => {
    reset(savedValues({ name: team.name, is_public: team.is_public }));
  }, [team.id, team.name, team.is_public, reset]);

  const save = useMutation({
    mutationFn: (values: TeamFormValues) => updateTeam(team.id, values),
    onSuccess: (updated) => {
      reset(savedValues(updated));
      return queryClient.invalidateQueries({ queryKey: teamsKey(userId) });
    },
    onError: (error) => {
      for (const { path, message } of fieldErrors(error)) {
        if (path === "name") setError("name", { type: "server", message });
      }
    },
  });
  const rejectedByServer = save.isError && fieldErrors(save.error).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("teamSettings.title")}</CardTitle>
        <CardDescription>{t("teamSettings.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          noValidate
          onSubmit={handleSubmit((values) => save.mutate(values))}
          className="flex flex-col gap-4"
        >
          <Field label={t("fields.teamName")} error={errors.name?.message}>
            {(props) => (
              <Input
                {...props}
                autoComplete="organization"
                placeholder={t("teams.form.teamNamePlaceholder")}
                {...register("name")}
              />
            )}
          </Field>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-primary"
              {...register("isPublic")}
            />
            <span>
              {t("teams.form.listInDirectory")}
              <span className="block text-muted-foreground">
                {t("teamSettings.listInDirectoryHint")}
              </span>
            </span>
          </label>
          {save.isError && !rejectedByServer && (
            <p role="alert" className="text-sm text-destructive">
              {describeError(save.error, t)}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" loading={save.isPending} disabled={!isDirty}>
              {t("teamSettings.submit")}
            </Button>
            {save.isSuccess && !isDirty && (
              <p role="status" className="text-sm text-muted-foreground">
                {t("teamSettings.saved")}
              </p>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
