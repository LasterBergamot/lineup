import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router";
import { createQueryClient } from "@/api/query-client";
import { AuthProvider } from "@/auth/provider";
import { RequireAuth } from "@/auth/require-auth";
import { BackendStatusProvider } from "@/backend-status/provider";
import { AppShell } from "@/components/app-shell";
import { LineupPage } from "@/pages/lineup-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { RosterPage } from "@/pages/roster-page";
import { SavedPage } from "@/pages/saved-page";
import { SignInPage } from "@/pages/sign-in-page";

/** The route table, separate from the router so tests can mount it in a `MemoryRouter`. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="sign-in" element={<SignInPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<LineupPage />} />
          <Route path="roster" element={<RosterPage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

/**
 * Root component. Order matters: the backend status check starts first thing on load (waking
 * a sleeping API while the shell already renders), the query client supplies retries to every
 * data region, auth sits inside the query client (it empties the cache on sign-out) and the
 * router inside all three so every page can use them.
 */
export function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <BackendStatusProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </BackendStatusProvider>
  );
}
