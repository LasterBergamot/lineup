import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { describeError, fieldErrors } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createTeam, teamsKey } from "@/features/teams/api";
import { teamFormSchema, type TeamFormValues } from "@/features/teams/schema";

/**
 * Name your team and create it; you become its owner. The checkbox lists only the name in the
 * shared opponent directory (default on, as the API does) and is said out loud because it is
 * the one thing in this form other clubs can see. On success the teams query is refreshed, which
 * is what moves the user out of onboarding.
 */
export function CreateTeamForm() {
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<TeamFormValues>({
    resolver: zodResolver(teamFormSchema),
    defaultValues: { name: "", isPublic: true },
  });

  const create = useMutation({
    mutationFn: (values: TeamFormValues) => createTeam(values),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: teamsKey(userId) }),
    onError: (error) => {
      for (const { path, message } of fieldErrors(error)) {
        if (path === "name") setError("name", { type: "server", message });
      }
    },
  });
  const rejectedByServer = create.isError && fieldErrors(create.error).length > 0;

  return (
    <form
      noValidate
      onSubmit={handleSubmit((values) => create.mutate(values))}
      className="flex flex-col gap-4"
    >
      <Field label="Team name" error={errors.name?.message}>
        {(props) => (
          <Input
            {...props}
            autoComplete="organization"
            placeholder="e.g. SZVTK"
            {...register("name")}
          />
        )}
      </Field>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-primary" {...register("isPublic")} />
        <span>
          List the team name in the opponent directory
          <span className="block text-muted-foreground">
            Other teams can then pick you as an opponent. Only the name is shown, never your roster
            or lineups. You can change this later.
          </span>
        </span>
      </label>
      {create.isError && !rejectedByServer && (
        <p role="alert" className="text-sm text-destructive">
          {describeError(create.error)}
        </p>
      )}
      <Button type="submit" loading={create.isPending} className="self-start">
        Create team
      </Button>
    </form>
  );
}
