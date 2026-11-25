import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listPlayers, playersKey, type Player } from "@/features/players/api";
import {
  createStaff,
  deleteStaff,
  listStaff,
  ROLE_LABELS,
  STAFF_ROLES,
  staffKey,
  staffOfRole,
  updateStaff,
  type Staff,
} from "@/features/staff/api";
import type { StaffFormValues } from "@/features/staff/schema";
import { StaffForm } from "@/features/staff/staff-form";
import type { Team } from "@/features/teams/api";

/** The form values of an existing entry; a source player who has left the roster counts as typed. */
function formValues(entry: Staff, roster: readonly Player[]): StaffFormValues {
  const onRoster = roster.some((player) => player.id === entry.source_player_id);
  return {
    role: entry.role,
    playerId: onRoster ? entry.source_player_id! : "",
    name: entry.name,
    isDefault: entry.is_default,
  };
}

/**
 * A team's staff (#289): coach, assistant coach, team leader and ball thrower, kept as a list of
 * names the lineup forms suggest. Add an entry by picking a roster player (the name is copied) or
 * typing a name, then edit, delete (`ConfirmButton`) or make it its role's default, which a new
 * lineup starts with. At most one default per role: the server clears the old one in the same
 * request, so the list is reloaded after every change (and after a failure, since a 404 usually
 * means another member deleted the entry meanwhile). Every member may do all of it; nothing is
 * gated on role. Saved lineups hold their own copy of the names, so nothing here changes them.
 *
 * The card reads the roster through the same query key as `PlayersCard`, so the two share one
 * request. Staff names are personal data: they stay in the query cache and form state only.
 */
export function StaffCard({ team }: { team: Team }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const key = staffKey(userId, team.id);
  const [editing, setEditing] = useState<string | null>(null);

  const staff = useQuery({ queryKey: key, queryFn: () => listStaff(team.id) });
  const roster = useQuery({
    queryKey: playersKey(userId, team.id),
    queryFn: () => listPlayers(team.id),
  });
  const players = roster.data ?? [];
  const refresh = () => queryClient.invalidateQueries({ queryKey: key });

  const remove = useMutation({
    mutationFn: (entry: Staff) => deleteStaff(entry),
    onSettled: refresh,
  });
  const makeDefault = useMutation({
    mutationFn: (entry: Staff) =>
      updateStaff(entry, { ...formValues(entry, players), isDefault: true }),
    onSettled: refresh,
  });
  const failed = remove.isError ? remove.error : makeDefault.isError ? makeDefault.error : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("staff.title")}</CardTitle>
        <CardDescription>{t("staff.description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <StaffForm
          label={t("staff.addTitle")}
          submitLabel={t("staff.add")}
          roster={players}
          save={(values) => createStaff(team.id, values)}
          onSettled={refresh}
          resetOnSuccess
        />
        <QueryBoundary
          query={staff}
          skeleton={
            <div className="flex flex-col gap-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          }
        >
          {(entries) =>
            entries.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("staff.empty")}</p>
            ) : (
              <div className="flex flex-col gap-4">
                {STAFF_ROLES.map((role) => {
                  const rows = staffOfRole(entries, role);
                  if (rows.length === 0) return null;
                  const headingId = `staff-${role}`;
                  return (
                    <section key={role} aria-labelledby={headingId} className="flex flex-col gap-2">
                      <h3 id={headingId} className="text-sm font-semibold">
                        {t(ROLE_LABELS[role])}
                      </h3>
                      <ul className="flex flex-col divide-y overflow-hidden rounded-lg border">
                        {rows.map((entry) => (
                          <li key={entry.id} className="p-3">
                            {editing === entry.id ? (
                              <StaffForm
                                label={t("staff.editLabel", {
                                  name: entry.name,
                                  role: t(ROLE_LABELS[entry.role]),
                                })}
                                submitLabel={t("staff.save")}
                                defaultValues={formValues(entry, players)}
                                roster={players}
                                save={(values) => updateStaff(entry, values)}
                                onSuccess={() => setEditing(null)}
                                onSettled={refresh}
                                onCancel={() => setEditing(null)}
                              />
                            ) : (
                              <StaffRow
                                entry={entry}
                                deleting={remove.isPending && remove.variables.id === entry.id}
                                defaulting={
                                  makeDefault.isPending && makeDefault.variables.id === entry.id
                                }
                                onEdit={() => setEditing(entry.id)}
                                onDelete={() => remove.mutate(entry)}
                                onMakeDefault={() => makeDefault.mutate(entry)}
                              />
                            )}
                          </li>
                        ))}
                      </ul>
                    </section>
                  );
                })}
                <p className="text-xs text-muted-foreground">{t("staff.hint")}</p>
              </div>
            )
          }
        </QueryBoundary>
        {failed !== null && (
          <p role="alert" className="text-sm text-destructive">
            {describeError(failed, t)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/** One staff row when it is not being edited: the name, the default badge and the actions. */
function StaffRow({
  entry,
  deleting,
  defaulting,
  onEdit,
  onDelete,
  onMakeDefault,
}: {
  entry: Staff;
  deleting: boolean;
  defaulting: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onMakeDefault: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <span className="text-sm font-medium break-words">{entry.name}</span>
        {entry.is_default && <Badge variant="primary">{t("staff.default")}</Badge>}
      </div>
      <div className="flex flex-wrap gap-2">
        {!entry.is_default && (
          <Button
            size="sm"
            variant="outline"
            aria-label={t("staff.makeDefaultLabel", {
              name: entry.name,
              role: t(ROLE_LABELS[entry.role]),
            })}
            loading={defaulting}
            onClick={onMakeDefault}
          >
            {t("staff.makeDefault")}
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          aria-label={t("staff.editLabel", { name: entry.name, role: t(ROLE_LABELS[entry.role]) })}
          onClick={onEdit}
        >
          {t("staff.edit")}
        </Button>
        <ConfirmButton
          label={t("staff.delete")}
          confirmLabel={t("staff.deleteConfirm")}
          ariaLabel={t("staff.deleteLabel", { name: entry.name, role: t(ROLE_LABELS[entry.role]) })}
          loading={deleting}
          onConfirm={onDelete}
        />
      </div>
    </div>
  );
}
