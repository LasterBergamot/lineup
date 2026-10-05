import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { createContext, useContext } from "react";

/**
 * - `loading`: the stored session is still being read (or a sign-in code exchanged).
 * - `signed-out`: nobody is signed in.
 * - `signed-in`: a session exists; `userId` is set.
 * - `unconfigured`: this build has no usable Supabase settings, so sign-in cannot work.
 */
export type AuthStatus = "loading" | "signed-out" | "signed-in" | "unconfigured";

/** The slice of Supabase's auth client the app uses (lets tests pass a stub). */
export type AuthClient = Pick<
  SupabaseClient["auth"],
  "onAuthStateChange" | "signInWithOAuth" | "signOut"
>;

export interface AuthValue {
  status: AuthStatus;
  session: Session | null;
  /** The Supabase user id (`sub` claim); the only identity detail the UI needs. */
  userId: string | null;
  /** Why sign-in is unavailable, when `status` is `unconfigured`. */
  configError: string | null;
  /** Set when the API rejected the token, so the sign-in page can explain why we are back. */
  notice: "session-expired" | null;
  /**
   * Starts Google sign-in (the browser leaves for Google and comes back to `/sign-in`).
   * Resolves to a user-facing error message if it could not start, otherwise `null`.
   */
  signInWithGoogle: () => Promise<string | null>;
  /** Ends the session on this device only. */
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthValue | null>(null);

/** Current auth state. Must be used inside `AuthProvider`. */
export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
