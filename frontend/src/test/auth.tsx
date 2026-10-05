import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { AppRoutes } from "@/app";
import type { AuthClient } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { BackendStatusProvider } from "@/backend-status/provider";

/** A session with just the fields the app reads; the token is a dummy, never a real one. */
export function fakeSession(userId = "11111111-1111-4111-8111-111111111111"): Session {
  return { access_token: "test-token", user: { id: userId } } as Session;
}

type Listener = (event: string, session: Session | null) => void;

/**
 * A stand-in for supabase-js's auth client (no network, no storage). Like the real one it reports
 * the stored session as soon as someone subscribes; `emit` pushes a later change.
 */
export function fakeAuthClient(initial: Session | null) {
  let listener: Listener | undefined;
  const unsubscribe = vi.fn();
  const client = {
    onAuthStateChange: vi.fn((callback: Listener) => {
      listener = callback;
      callback("INITIAL_SESSION", initial);
      return { data: { subscription: { unsubscribe } } };
    }),
    signInWithOAuth: vi.fn(async (): Promise<{ data: object; error: Error | null }> => ({
      data: {},
      error: null,
    })),
    signOut: vi.fn(async () => {
      listener?.("SIGNED_OUT", null);
      return { error: null };
    }),
  };
  return {
    client: client as unknown as AuthClient,
    mocks: client,
    unsubscribe,
    emit: (event: string, session: Session | null) => listener?.(event, session),
  };
}

/** A query client that never retries, so failures show up immediately in tests. */
export function testQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

/** Renders the whole route table at `path` with a fake auth client and a healthy backend. */
export function renderApp(path: string, session: Session | null) {
  const auth = fakeAuthClient(session);
  const queryClient = testQueryClient();
  const view = render(
    <BackendStatusProvider probe={async () => "ok"}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider client={auth.client}>
          <MemoryRouter initialEntries={[path]}>
            <AppRoutes />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    </BackendStatusProvider>,
  );
  return { ...view, auth, queryClient };
}

/** Builds the JSON a `GET /teams` answers with. */
export function teamsPage(...names: string[]) {
  return {
    items: names.map((name, i) => ({
      id: `00000000-0000-4000-8000-00000000000${i + 1}`,
      name,
      created_by: "11111111-1111-4111-8111-111111111111",
      is_public: true,
      created_at: "2026-10-05T10:00:00",
      role: "owner",
    })),
    total: names.length,
    limit: 200,
    offset: 0,
  };
}
