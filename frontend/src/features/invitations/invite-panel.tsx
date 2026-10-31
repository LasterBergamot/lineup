import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createInvitation,
  DEFAULT_EXPIRY,
  EXPIRY_CHOICES,
  invitationsKey,
  listInvitations,
  revokeInvitation,
  type ExpiryHours,
  type InvitationCreated,
} from "@/features/invitations/api";
import type { Team } from "@/features/teams/api";
import { formatDateTime } from "@/lib/format-date";

const EXPIRY_LABELS = {
  2: "invites.hours2",
  24: "invites.hours24",
  72: "invites.hours72",
} as const satisfies Record<ExpiryHours, string>;

/**
 * The owner's invite tools: make a link (2 hours, 24 hours or 3 days), copy or share it, and
 * revoke the ones still active. A new link is shown once, here, and held only in this component's
 * state: the API stores just a hash of the code, and nothing here writes it to storage or logs it.
 * Anyone who opens the link while signed in joins as a member, so the text says to send it only
 * to the people who should see the roster.
 */
export function InvitePanel({ team }: { team: Team }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const key = invitationsKey(userId, team.id);
  const [hours, setHours] = useState<ExpiryHours>(DEFAULT_EXPIRY);
  const [created, setCreated] = useState<InvitationCreated | null>(null);
  const [copy, setCopy] = useState<"idle" | "copied" | "failed">("idle");

  const active = useQuery({ queryKey: key, queryFn: () => listInvitations(team.id) });
  const create = useMutation({
    mutationFn: () => createInvitation(team.id, hours),
    onSuccess: (invitation) => {
      setCreated(invitation);
      setCopy("idle");
      void queryClient.invalidateQueries({ queryKey: key });
    },
  });
  const revoke = useMutation({
    mutationFn: (invitationId: string) => revokeInvitation(team.id, invitationId),
    onSuccess: (_data, invitationId) => {
      if (created?.id === invitationId) setCreated(null);
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: key }),
  });

  async function copyLink(link: InvitationCreated) {
    try {
      await navigator.clipboard.writeText(link.url);
      setCopy("copied");
    } catch {
      setCopy("failed");
    }
  }

  async function shareLink(link: InvitationCreated) {
    try {
      await navigator.share({ title: t("invites.shareTitle", { team: team.name }), url: link.url });
    } catch {
      // Closing the share sheet rejects the promise; there is nothing to report.
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("invites.title")}</CardTitle>
        <CardDescription>{t("invites.description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <form
          className="flex flex-col items-start gap-3 sm:flex-row sm:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            create.mutate();
          }}
        >
          <Field label={t("invites.expiry")} className="w-full sm:w-56">
            {(props) => (
              <Select
                {...props}
                value={hours}
                onChange={(event) => setHours(Number(event.target.value) as ExpiryHours)}
              >
                {EXPIRY_CHOICES.map((choice) => (
                  <option key={choice} value={choice}>
                    {t(EXPIRY_LABELS[choice])}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Button type="submit" loading={create.isPending}>
            {t("invites.create")}
          </Button>
        </form>
        {create.isError && (
          <p role="alert" className="text-sm text-destructive">
            {describeError(create.error, t)}
          </p>
        )}

        {created && (
          <div className="flex flex-col gap-3 border bg-muted p-4">
            <Field label={t("invites.created")}>
              {(props) => (
                <Input
                  {...props}
                  readOnly
                  value={created.url}
                  onFocus={(event) => event.currentTarget.select()}
                />
              )}
            </Field>
            <p className="text-sm text-muted-foreground">
              {t("invites.shownOnce", { date: formatDateTime(created.expires_at, i18n.language) })}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" onClick={() => void copyLink(created)}>
                {t("invites.copy")}
              </Button>
              {typeof navigator.share === "function" && (
                <Button variant="outline" onClick={() => void shareLink(created)}>
                  {t("invites.share")}
                </Button>
              )}
              {copy !== "idle" && (
                <p
                  role="status"
                  className={copy === "failed" ? "text-sm text-destructive" : "text-sm"}
                >
                  {t(copy === "copied" ? "invites.copied" : "invites.copyFailed")}
                </p>
              )}
            </div>
          </div>
        )}

        <section aria-labelledby="active-links" className="flex flex-col gap-3">
          <h3 id="active-links" className="text-sm font-medium">
            {t("invites.activeTitle")}
          </h3>
          <QueryBoundary query={active} skeleton={<Skeleton className="h-10 w-full" />}>
            {(links) =>
              links.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("invites.none")}</p>
              ) : (
                <ul className="flex flex-col divide-y border">
                  {links.map((link) => (
                    <li
                      key={link.id}
                      className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm"
                    >
                      <span>
                        {t("invites.item", {
                          created: formatDateTime(link.created_at, i18n.language),
                          expires: formatDateTime(link.expires_at, i18n.language),
                        })}
                      </span>
                      <ConfirmButton
                        label={t("invites.revoke")}
                        confirmLabel={t("invites.revokeConfirm")}
                        loading={revoke.isPending}
                        onConfirm={() => revoke.mutate(link.id)}
                      />
                    </li>
                  ))}
                </ul>
              )
            }
          </QueryBoundary>
          {revoke.isError && (
            <p role="alert" className="text-sm text-destructive">
              {describeError(revoke.error, t)}
            </p>
          )}
        </section>
      </CardContent>
    </Card>
  );
}
