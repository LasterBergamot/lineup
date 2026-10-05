import { useState } from "react";
import { Navigate, useLocation } from "react-router";
import { useAuth } from "@/auth/context";
import { readReturnPath, rememberReturnPath, safeReturnPath } from "@/auth/return-path";
import { BackendStatusBanner } from "@/backend-status/banner";
import { Brand } from "@/components/brand";
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
  const { status, configError, notice, signInWithGoogle } = useAuth();
  const location = useLocation();
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "signed-in") return <Navigate to={readReturnPath()} replace />;

  const from = safeReturnPath((location.state as { from?: string } | null)?.from);

  async function start() {
    setStarting(true);
    setError(null);
    rememberReturnPath(from);
    const failure = await signInWithGoogle();
    // On success the browser is already leaving for Google, so the button stays busy.
    if (failure) {
      setError(failure);
      setStarting(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <BackendStatusBanner />
      <main className="flex flex-1 items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="gap-4">
            <Brand />
            <CardTitle>Sign in</CardTitle>
            <CardDescription>
              Sign in with your Google account to manage your team&apos;s roster and lineups.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {status === "loading" ? (
              <div role="status" aria-busy="true" aria-label="Loading">
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <>
                {notice === "session-expired" && (
                  <p role="status" className="text-sm text-muted-foreground">
                    Your session has ended. Please sign in again.
                  </p>
                )}
                {status === "unconfigured" && (
                  <p role="alert" className="text-sm text-destructive">
                    {configError}
                  </p>
                )}
                {error && (
                  <p role="alert" className="text-sm text-destructive">
                    {error}
                  </p>
                )}
                <Button
                  size="lg"
                  loading={starting}
                  disabled={status === "unconfigured"}
                  onClick={() => void start()}
                >
                  Continue with Google
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
