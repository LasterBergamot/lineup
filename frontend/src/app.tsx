import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { I18nextProvider } from "react-i18next";
import { createBrowserRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { createQueryClient } from "@/api/query-client";
import { AuthProvider } from "@/auth/provider";
import { BackendStatusProvider } from "@/backend-status/provider";
import { ToastProvider } from "@/components/ui/toast";
import { i18n } from "@/i18n";
import { routes } from "@/routes";

/**
 * Root component. Order matters: the i18n provider is outermost so every string, even the
 * backend banner, is translated; the backend status check starts first thing on load (waking
 * a sleeping API while the shell already renders), the query client supplies retries to every
 * data region, auth sits inside the query client (it empties the cache on sign-out), the toast
 * stack inside auth and the router inside all of them so every page can use them. The browser
 * router is created once per mounted app (like the query client), not at module load, so
 * importing this file in a test starts no router.
 */
export function App() {
  const [queryClient] = useState(createQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <I18nextProvider i18n={i18n}>
      <BackendStatusProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <ToastProvider>
              <RouterProvider router={router} />
            </ToastProvider>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>
    </I18nextProvider>
  );
}
