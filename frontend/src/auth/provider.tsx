import { useQueryClient } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AuthConfigError } from "@/auth/config";
import { AuthContext, type AuthClient, type AuthStatus, type AuthValue } from "@/auth/context";
import { onUnauthorized } from "@/auth/events";
import { clearReturnPath } from "@/auth/return-path";
import { getSupabase } from "@/auth/supabase";

/** Resolves the auth client, or the reason sign-in cannot work in this build. */
function resolveClient(client: AuthClient | undefined): {
  auth?: AuthClient;
  configError?: string;
} {
  if (client) return { auth: client };
  try {
    return { auth: getSupabase().auth };
  } catch (error) {
    if (error instanceof AuthConfigError) return { configError: error.message };
    throw error;
  }
}

/**
 * Owns the signed-in session. supabase-js reads the stored session (and finishes a Google
 * sign-in when the browser comes back with a code) and reports it through
 * `onAuthStateChange`; this provider mirrors that into React state. It also:
 * - empties the query cache whenever nobody is signed in, so one person's data is never
 *   shown to the next person on the same device;
 * - signs out when the API answers `401` to a request that carried a token.
 *
 * Tokens stay inside supabase-js. Nothing here logs or exposes them beyond `session`.
 */
export function AuthProvider({ children, client }: { children: ReactNode; client?: AuthClient }) {
  const queryClient = useQueryClient();
  const [{ auth, configError }] = useState(() => resolveClient(client));
  const [status, setStatus] = useState<AuthStatus>(auth ? "loading" : "unconfigured");
  const [session, setSession] = useState<Session | null>(null);
  const [notice, setNotice] = useState<AuthValue["notice"]>(null);

  const apply = useCallback(
    (next: Session | null) => {
      setSession(next);
      setStatus(next ? "signed-in" : "signed-out");
      if (!next) queryClient.clear();
      else setNotice(null);
    },
    [queryClient],
  );

  useEffect(() => {
    if (!auth) return;
    const { data } = auth.onAuthStateChange((_event, next) => apply(next));
    const stopListening = onUnauthorized(() => {
      setNotice("session-expired");
      void auth.signOut({ scope: "local" });
      apply(null);
    });
    return () => {
      data.subscription.unsubscribe();
      stopListening();
    };
  }, [auth, apply]);

  const signInWithGoogle = useCallback(async () => {
    const { error } = await auth!.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/sign-in` },
    });
    return error ? "We couldn't start the sign-in. Please try again." : null;
  }, [auth]);

  const signOut = useCallback(async () => {
    setNotice(null);
    clearReturnPath();
    await auth!.signOut({ scope: "local" });
  }, [auth]);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      session,
      userId: session?.user.id ?? null,
      configError: configError ?? null,
      notice,
      signInWithGoogle,
      signOut,
    }),
    [status, session, configError, notice, signInWithGoogle, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
