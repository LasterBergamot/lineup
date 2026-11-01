import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listMembers, membersKey, removeMember, transferOwnership } from "@/features/members/api";
import { teamsKey, type Team } from "@/features/teams/api";
import { roleKey } from "@/features/teams/role";
import { formatDateTime } from "@/lib/format-date";

/**
 * The people in a team. A row shows the member's `display_name` (their Google name, which the API
 * fills in the next time they open the app), with "(you)" on your own. A member with no name yet
 * is "You" or "Member 1", "Member 2" … in the API's order. No user id or e-mail address is ever
 * shown. Owners can remove a member or hand the team over; everyone can leave. Each action asks to be confirmed
 * first. The server decides what is allowed: a 409 on leaving means "the only owner", the other
 * failures use the generic messages.
 */
export function MembersList({ team }: { team: Team }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const key = membersKey(userId, team.id);
  const isOwner = team.role === "owner";
  const [problem, setProblem] = useState<unknown>(null);

  const members = useQuery({ queryKey: key, queryFn: () => listMembers(team.id) });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: key });
  const failed = { onMutate: () => setProblem(null), onError: setProblem };

  const remove = useMutation({
    mutationFn: (memberId: string) => removeMember(team.id, memberId),
    ...failed,
    onSettled: refresh,
  });
  const transfer = useMutation({
    mutationFn: (memberId: string) => transferOwnership(team.id, memberId),
    ...failed,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: teamsKey(userId) }),
    onSettled: refresh,
  });
  const leave = useMutation({
    mutationFn: () => removeMember(team.id, userId!),
    ...failed,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: key });
      return queryClient.invalidateQueries({ queryKey: teamsKey(userId) });
    },
  });

  const lastOwner = problem instanceof ApiError && problem.status === 409;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("members.listTitle")}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <QueryBoundary
          query={members}
          skeleton={
            <div className="flex flex-col gap-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          }
        >
          {(rows) => {
            let others = 0;
            return (
              <ul className="flex flex-col divide-y overflow-hidden rounded-lg border">
                {rows.map((member) => {
                  const number = member.is_you ? 0 : ++others;
                  const name = member.display_name;
                  const title = member.is_you
                    ? name
                      ? t("members.youNamed", { name })
                      : t("members.you")
                    : (name ?? t("members.member", { number }));
                  return (
                    <li
                      key={member.user_id}
                      className="flex flex-wrap items-center justify-between gap-3 p-3"
                    >
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <span className="flex items-center gap-2 text-sm font-medium">
                          {title}
                          <Badge variant={member.role === "owner" ? "primary" : "neutral"}>
                            {t(roleKey(member.role))}
                          </Badge>
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {t("members.joined", {
                            date: formatDateTime(member.joined_at, i18n.language),
                          })}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {member.is_you ? (
                          <ConfirmButton
                            label={t("members.leave")}
                            confirmLabel={t("members.leaveConfirm")}
                            loading={leave.isPending}
                            onConfirm={() => leave.mutate()}
                          />
                        ) : (
                          isOwner && (
                            <>
                              <ConfirmButton
                                label={t("members.makeOwner")}
                                confirmLabel={t("members.makeOwnerConfirm")}
                                ariaLabel={
                                  name
                                    ? t("members.makeOwnerNamedLabel", { name })
                                    : t("members.makeOwnerLabel", { number })
                                }
                                loading={transfer.isPending}
                                onConfirm={() => transfer.mutate(member.user_id)}
                              />
                              <ConfirmButton
                                label={t("members.remove")}
                                confirmLabel={t("members.removeConfirm")}
                                ariaLabel={
                                  name
                                    ? t("members.removeNamedLabel", { name })
                                    : t("members.removeLabel", { number })
                                }
                                loading={remove.isPending}
                                onConfirm={() => remove.mutate(member.user_id)}
                              />
                            </>
                          )
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            );
          }}
        </QueryBoundary>
        {problem !== null && (
          <p role="alert" className="text-sm text-destructive">
            {lastOwner ? t("members.lastOwner") : describeError(problem, t)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
