import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router";
import { AppShell } from "@/components/app-shell";
import { LineupPage } from "@/pages/lineup-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { RosterPage } from "@/pages/roster-page";
import { SavedPage } from "@/pages/saved-page";

/** The route table, separate from the router so tests can mount it in a `MemoryRouter`. */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<LineupPage />} />
        <Route path="roster" element={<RosterPage />} />
        <Route path="saved" element={<SavedPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

/** Root component: data-fetching provider, then the browser router. */
export function App() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
