import type { RouteObject } from "react-router";
import { RequireAuth } from "@/auth/require-auth";
import { AppShell } from "@/components/app-shell";
import { JoinPage } from "@/pages/join-page";
import { LineupPage } from "@/pages/lineup-page";
import { MembersPage } from "@/pages/members-page";
import { NotFoundPage } from "@/pages/not-found-page";
import { RosterPage } from "@/pages/roster-page";
import { SavedPage } from "@/pages/saved-page";
import { SignInPage } from "@/pages/sign-in-page";

/**
 * The app's route table, mounted by `App` (`app.tsx`) in `createBrowserRouter`. It is a data
 * router's route objects, not `<Routes>`, because blocking an in-app navigation (`useBlocker`, the
 * unsaved-changes guard) works only under a data router. Tests mount the same table in
 * `createMemoryRouter` (`testRouter` / `renderApp` in `src/test/auth.tsx`).
 * `/sign-in` and `/join/:code` stay outside `RequireAuth` on purpose: the invite preview is public.
 */
export const routes: RouteObject[] = [
  { path: "sign-in", element: <SignInPage /> },
  { path: "join/:code", element: <JoinPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <LineupPage /> },
          { path: "roster", element: <RosterPage /> },
          { path: "saved", element: <SavedPage /> },
          { path: "members", element: <MembersPage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
