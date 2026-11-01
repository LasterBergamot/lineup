import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { I18nextProvider } from "react-i18next";
import { BrowserRouter, Route, Routes } from "react-router";
import { createQueryClient } from "@/api/query-client";
import { AuthProvider } from "@/auth/provider";
import { RequireAuth } from "@/auth/require-auth";
import { BackendStatusProvider } from "@/backend-status/provider";
import { AppShell } from "@/components/app-shell";
import { ToastProvider } from "@/components/ui/toast";
import { i18n } from "@/i18n";
import { JoinPage } from "@/pages/join-page";
import { LineupPage } from "@/pages/lineup-page";
import { MembersPage } from "@/pages/members-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { RosterPage } from "@/pages/roster-page";
import { SavedPage } from "@/pages/saved-page";
import { SignInPage } from "@/pages/sign-in-page";

/** The route table, separate from the router so tests can mount it in a `MemoryRouter`. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="sign-in" element={<SignInPage />} />
      <Route path="join/:code" element={<JoinPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<LineupPage />} />
          <Route path="roster" element={<RosterPage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

/**
 * Root component. Order matters: the i18n provider is outermost so every string, even the
 * backend banner, is translated; the backend status check starts first thing on load (waking
 * a sleeping API while the shell already renders), the query client supplies retries to every
 * data region, auth sits inside the query client (it empties the cache on sign-out), the toast
 * stack inside auth and the router inside all of them so every page can use them.
 */
export function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <I18nextProvider i18n={i18n}>
      <BackendStatusProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <ToastProvider>
              <BrowserRouter>
                <AppRoutes />
              </BrowserRouter>
            </ToastProvider>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>
    </I18nextProvider>
  );
}
