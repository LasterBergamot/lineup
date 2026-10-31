import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { ApiError, describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { clearReturnPath, rememberReturnPath } from "@/auth/return-path";
import { BackendStatusBanner } from "@/backend-status/banner";
import { Brand } from "@/components/brand";
import { LanguageSwitch } from "@/components/language-switch";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  acceptInvitation,
  invitationPreviewKey,
  previewInvitation,
  type InvitationPreview,
} from "@/features/invitations/api";
import { teamsKey } from "@/features/teams/api";
import { formatDateTime } from "@/lib/format-date";

/** Which dead end a failed call means: a code we don't know, or one that expired or was revoked. */
function deadEnd(error: unknown): "unknown" | "gone" | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status === 404 || error.status === 422) return "unknown";
  if (error.status === 410) return "gone";
  return null;
}

/**
 * Where an invite link lands (`/join/:code`). It sits outside the sign-in guard on purpose: the
 * preview ("Join <team>?") is public, so the visitor sees what they are joining before they are
 * asked to sign in. Signed out, the button remembers this path and goes to Google; the sign-in
 * page sends them back here, and only then does a second button actually join (a link must never
 * join anyone by merely being opened).
 *
 * The code is a join credential, so it lives in the URL and in memory only, plus the remembered
 * return path for the length of the Google round trip (a tab-scoped `sessionStorage` entry). That
 * entry is cleared as soon as the visitor is back and signed in, after joining, and on sign-out;
 * after joining the page is replaced in the history so the code is not left behind.
 */
export function JoinPage() {
  const { t, i18n } = useTranslation();
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { status, userId, configError, signInWithGoogle } = useAuth();
  const [signInFailed, setSignInFailed] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (status === "signed-in") clearReturnPath();
  }, [status]);

  // Wait until the stored session has been read: finding nobody signed in empties the whole query
  // cache (see `AuthProvider`), which would throw this request away and send it a second time.
  const preview = useQuery({
    queryKey: invitationPreviewKey(code),
    queryFn: () => previewInvitation(code),
    enabled: status !== "loading",
    staleTime: 60_000,
  });
  const accept = useMutation({
    mutationFn: () => acceptInvitation(code),
    onSuccess: async () => {
      clearReturnPath();
      await queryClient.invalidateQueries({ queryKey: teamsKey(userId) });
      navigate("/", { replace: true });
    },
  });

  async function startSignIn() {
    setStarting(true);
    setSignInFailed(false);
    rememberReturnPath(`/join/${encodeURIComponent(code)}`);
    const failure = await signInWithGoogle();
    // On success the browser is already leaving for Google, so the button stays busy.
    if (failure) {
      setSignInFailed(true);
      setStarting(false);
    }
  }

  const dead = deadEnd(preview.error) ?? deadEnd(accept.error);

  function renderCard(invitation: InvitationPreview) {
    return (
      <>
        <CardHeader className="gap-4">
          <Brand />
          <CardTitle>{t("join.title", { team: invitation.team_name })}</CardTitle>
          <CardDescription>
            {invitation.invited_by_name
              ? t("join.invitedBy", { name: invitation.invited_by_name })
              : t("join.invitedByUnknown")}{" "}
            {t("join.expires", { date: formatDateTime(invitation.expires_at, i18n.language) })}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {status === "unconfigured" && (
            <p role="alert" className="text-sm text-destructive">
              {configError}
            </p>
          )}
          {signInFailed && (
            <p role="alert" className="text-sm text-destructive">
              {t("auth.signIn.startFailed")}
            </p>
          )}
          {accept.isError && !dead && (
            <p role="alert" className="text-sm text-destructive">
              {describeError(accept.error, t)}
            </p>
          )}
          {status === "loading" ? (
            <div role="status" aria-busy="true" aria-label={t("common.loading")}>
              <Skeleton className="h-10 w-full" />
            </div>
          ) : status === "signed-in" ? (
            <Button size="lg" loading={accept.isPending} onClick={() => accept.mutate()}>
              {t("join.accept")}
            </Button>
          ) : (
            <Button
              size="lg"
              loading={starting}
              disabled={status === "unconfigured"}
              onClick={() => void startSignIn()}
            >
              {t("join.signIn")}
            </Button>
          )}
        </CardContent>
      </>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <BackendStatusBanner />
      <div className="flex justify-end p-4 pb-0">
        <LanguageSwitch />
      </div>
      <main className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md">
          {dead ? (
            <>
              <CardHeader className="gap-4">
                <Brand />
                <CardTitle>{t(dead === "gone" ? "join.goneTitle" : "join.unknownTitle")}</CardTitle>
                <CardDescription>
                  {t(dead === "gone" ? "join.goneBody" : "join.unknownBody")}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild variant="outline">
                  <Link to="/">{t("join.home")}</Link>
                </Button>
              </CardContent>
            </>
          ) : (
            <QueryBoundary
              query={preview}
              skeleton={
                <div className="flex flex-col gap-4 p-6">
                  <Skeleton className="h-8 w-48" />
                  <Skeleton className="h-10 w-full" />
                </div>
              }
            >
              {renderCard}
            </QueryBoundary>
          )}
        </Card>
      </main>
    </div>
  );
}
