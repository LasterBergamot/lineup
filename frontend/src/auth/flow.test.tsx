import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach } from "vitest";
import { ApiError } from "@/api/errors";
import { AuthProvider } from "@/auth/provider";
import { notifyUnauthorized } from "@/auth/events";
import { BackendStatusProvider } from "@/backend-status/provider";
import { AppRoutes } from "@/app";
import { fakeAuthClient, fakeSession, renderApp, teamsPage, testQueryClient } from "@/test/auth";

const { listTeams, createTeam } = vi.hoisted(() => ({ listTeams: vi.fn(), createTeam: vi.fn() }));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams,
  createTeam,
}));

beforeEach(() => {
  listTeams.mockReset();
  createTeam.mockReset();
  sessionStorage.clear();
  listTeams.mockResolvedValue(teamsPage("SZVTK").items);
});

describe("signed out", () => {
  it("sends a visitor to the sign-in page", async () => {
    renderApp("/roster", null);
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(listTeams).not.toHaveBeenCalled();
  });

  it("starts Google sign-in, returning to this site's /sign-in page", async () => {
    const { auth } = renderApp("/roster", null);
    await userEvent.click(await screen.findByRole("button", { name: "Continue with Google" }));
    expect(auth.mocks.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/sign-in` },
    });
    // The browser is leaving for Google, so the button keeps spinning instead of re-enabling.
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeDisabled();
    expect(sessionStorage.getItem("lineup-return-to")).toBe("/roster");
  });

  it("explains a failed start and lets the visitor try again", async () => {
    const { auth } = renderApp("/", null);
    auth.mocks.signInWithOAuth.mockResolvedValueOnce({ data: {}, error: new Error("boom") });
    await userEvent.click(await screen.findByRole("button", { name: "Continue with Google" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("couldn't start the sign-in");
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeEnabled();
  });

  it("shows the wake-up state of the backend on the sign-in page too", async () => {
    render(
      <BackendStatusProvider probe={async () => "unavailable"}>
        <QueryClientProvider client={testQueryClient()}>
          <AuthProvider client={fakeAuthClient(null).client}>
            <MemoryRouter initialEntries={["/sign-in"]}>
              <AppRoutes />
            </MemoryRouter>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    // The provider mounted (and fired its health check) although nobody is signed in.
    await waitFor(() => expect(screen.getByRole("button", { name: /Continue/ })).toBeEnabled());
  });

  it("explains that sign-in is not configured instead of failing silently", async () => {
    render(
      <BackendStatusProvider probe={async () => "ok"}>
        <QueryClientProvider client={testQueryClient()}>
          <AuthProvider>
            <MemoryRouter initialEntries={["/sign-in"]}>
              <AppRoutes />
            </MemoryRouter>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("VITE_SUPABASE_URL");
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeDisabled();
  });

  it("shows a skeleton until the stored session has been read", () => {
    const auth = fakeAuthClient(null);
    auth.mocks.onAuthStateChange.mockImplementation(() => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    }));
    render(
      <BackendStatusProvider probe={async () => "ok"}>
        <QueryClientProvider client={testQueryClient()}>
          <AuthProvider client={auth.client}>
            <MemoryRouter initialEntries={["/"]}>
              <AppRoutes />
            </MemoryRouter>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>,
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("shows the sign-in skeleton while the session is loading on /sign-in", () => {
    const auth = fakeAuthClient(null);
    auth.mocks.onAuthStateChange.mockImplementation(() => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    }));
    render(
      <BackendStatusProvider probe={async () => "ok"}>
        <QueryClientProvider client={testQueryClient()}>
          <AuthProvider client={auth.client}>
            <MemoryRouter initialEntries={["/sign-in"]}>
              <AppRoutes />
            </MemoryRouter>
          </AuthProvider>
        </QueryClientProvider>
      </BackendStatusProvider>,
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Continue with Google" })).not.toBeInTheDocument();
  });
});

describe("coming back from Google", () => {
  it("forwards a signed-in visitor on /sign-in to the page they wanted", async () => {
    sessionStorage.setItem("lineup-return-to", "/saved");
    renderApp("/sign-in", fakeSession());
    expect(await screen.findByRole("heading", { name: "Saved lineups" })).toBeInTheDocument();
  });

  it("ignores a remembered path that leaves the site", async () => {
    sessionStorage.setItem("lineup-return-to", "//evil.example/phish");
    renderApp("/sign-in", fakeSession());
    expect(await screen.findByRole("heading", { name: "Lineup" })).toBeInTheDocument();
  });

  it("lets a session arriving later move the visitor into the app", async () => {
    const { auth } = renderApp("/sign-in", null);
    await screen.findByRole("heading", { name: "Sign in" });
    auth.emit("SIGNED_IN", fakeSession());
    expect(await screen.findAllByText("SZVTK")).not.toHaveLength(0);
  });
});

describe("onboarding", () => {
  beforeEach(() => listTeams.mockResolvedValue([]));

  it("offers to create a team, with the invite-link path visible but disabled", async () => {
    renderApp("/", fakeSession());
    expect(await screen.findByRole("heading", { name: "Welcome to Lineup" })).toBeInTheDocument();
    expect(screen.getByLabelText("Invite link")).toBeDisabled();
    expect(screen.queryByRole("heading", { name: "Lineup" })).not.toBeInTheDocument();
  });

  it("creates the team, then shows the app with the team in the shell", async () => {
    createTeam.mockImplementation(async () => {
      listTeams.mockResolvedValue(teamsPage("Brand New").items);
      return teamsPage("Brand New").items[0];
    });
    renderApp("/", fakeSession());
    await userEvent.type(await screen.findByLabelText("Team name"), "  Brand New ");
    await userEvent.click(screen.getByRole("button", { name: "Create team" }));
    expect(createTeam).toHaveBeenCalledWith({ name: "Brand New", isPublic: true });
    expect(await screen.findByRole("heading", { name: "Lineup" })).toBeInTheDocument();
    expect(screen.getAllByText("Brand New").length).toBeGreaterThan(0);
  });

  it("can keep the team out of the opponent directory", async () => {
    createTeam.mockResolvedValue(teamsPage("Quiet").items[0]);
    renderApp("/", fakeSession());
    await userEvent.type(await screen.findByLabelText("Team name"), "Quiet");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Create team" }));
    expect(createTeam).toHaveBeenCalledWith({ name: "Quiet", isPublic: false });
  });

  it("validates the name before calling the API", async () => {
    renderApp("/", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Create team" }));
    expect(await screen.findByText("Team name is required")).toBeInTheDocument();
    expect(createTeam).not.toHaveBeenCalled();
  });

  it("shows the API's field message for a rejected name", async () => {
    createTeam.mockRejectedValue(
      new ApiError(422, { detail: [{ loc: ["body", "name"], msg: "Value error, Bad name" }] }),
    );
    renderApp("/", fakeSession());
    await userEvent.type(await screen.findByLabelText("Team name"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Create team" }));
    expect(await screen.findByText("Bad name")).toBeInTheDocument();
  });

  it("shows a generic message for any other failure", async () => {
    createTeam.mockRejectedValue(new ApiError(500));
    renderApp("/", fakeSession());
    await userEvent.type(await screen.findByLabelText("Team name"), "X");
    await userEvent.click(screen.getByRole("button", { name: "Create team" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side");
  });
});

describe("when the API misbehaves", () => {
  it("shows a retry box for a 503 rather than sending the user back to sign-in", async () => {
    listTeams.mockRejectedValueOnce(new ApiError(503));
    renderApp("/", fakeSession());
    expect(await screen.findByRole("alert")).toHaveTextContent("busy or starting up");
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findAllByText("SZVTK")).not.toHaveLength(0);
  });

  it("signs out and explains why when the API rejects the token (401)", async () => {
    const { auth } = renderApp("/roster", fakeSession());
    await screen.findAllByText("SZVTK");
    notifyUnauthorized();
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("session has ended");
    expect(auth.mocks.signOut).toHaveBeenCalledWith({ scope: "local" });
  });

  it("forgets the previous user's data when signing out", async () => {
    const { queryClient } = renderApp("/", fakeSession());
    await screen.findAllByText("SZVTK");
    expect(queryClient.getQueryCache().getAll().length).toBeGreaterThan(0);
    await userEvent.click(screen.getAllByRole("button", { name: "Sign out" })[0]!);
    await screen.findByRole("heading", { name: "Sign in" });
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("stops listening when the app unmounts", () => {
    const { auth, unmount } = renderApp("/", null);
    unmount();
    expect(auth.unsubscribe).toHaveBeenCalledOnce();
  });
});
