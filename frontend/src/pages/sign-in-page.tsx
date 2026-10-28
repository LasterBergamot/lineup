import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { readReturnPath, rememberReturnPath, safeReturnPath } from "@/auth/return-path";
import { BackendStatusBanner } from "@/backend-status/banner";
import { Brand } from "@/components/brand";
import { LanguageSwitch } from "@/components/language-switch";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Where visitors sign in with Google. It is also where Google sends them back to, so a signed-in
 * visitor is forwarded on to the page they originally wanted. The backend wake-up banner shows
 * here too: the health check starts on page load, so a sleeping free-tier API is already booting
 * while the visitor is still choosing an account.
 */
export function SignInPage() {
  const { t } = useTranslation();
  const { status, configError, notice, signInWithGoogle } = useAuth();
  const location = useLocation();
  const [starting, setStarting] = useState(false);
  const [failed, setFailed] = useState(false);

  if (status === "signed-in") return <Navigate to={readReturnPath()} replace />;

  const from = safeReturnPath((location.state as { from?: string } | null)?.from);

  async function start() {
    setStarting(true);
    setFailed(false);
    rememberReturnPath(from);
    const failure = await signInWithGoogle();
    // On success the browser is already leaving for Google, so the button stays busy.
    if (failure) {
      setFailed(true);
      setStarting(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <BackendStatusBanner />
      <div className="flex justify-end p-4 pb-0">
        <LanguageSwitch />
      </div>
      <main className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="gap-4">
            <Brand />
            <CardTitle>{t("auth.signIn.title")}</CardTitle>
            <CardDescription>{t("auth.signIn.description")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {status === "loading" ? (
              <div role="status" aria-busy="true" aria-label={t("common.loading")}>
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <>
                {notice === "session-expired" && (
                  <p role="status" className="text-sm text-muted-foreground">
                    {t("auth.signIn.sessionEnded")}
                  </p>
                )}
                {status === "unconfigured" && (
                  <p role="alert" className="text-sm text-destructive">
                    {configError}
                  </p>
                )}
                {failed && (
                  <p role="alert" className="text-sm text-destructive">
                    {t("auth.signIn.startFailed")}
                  </p>
                )}
                <Button
                  size="lg"
                  loading={starting}
                  disabled={status === "unconfigured"}
                  onClick={() => void start()}
                >
                  {t("auth.signIn.continue")}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
