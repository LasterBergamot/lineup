import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useNavigationType } from "react-router";
import { ApiError } from "@/api/errors";
import { fakeSession, renderApp, teamsPage } from "@/test/auth";

const { listTeams, previewInvitation, acceptInvitation } = vi.hoisted(() => ({
  listTeams: vi.fn(),
  previewInvitation: vi.fn(),
  acceptInvitation: vi.fn(),
}));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams,
}));
vi.mock("@/features/invitations/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/invitations/api")>()),
  previewInvitation,
  acceptInvitation,
}));

const CODE = "Zk3_-abcDEF";
const PREVIEW = {
  team_name: "Ferencváros",
  invited_by_name: "Ann Coach",
  expires_at: "2026-11-01T10:00:00",
};
const RETURN_KEY = "lineup-return-to";

/** Shows how the last navigation happened, so a test can tell a replace from a push. */
function NavigationProbe() {
  return <p data-testid="nav-type">{useNavigationType()}</p>;
}

beforeEach(() => {
  for (const mock of [listTeams, previewInvitation, acceptInvitation]) mock.mockReset();
  sessionStorage.clear();
  listTeams.mockResolvedValue(teamsPage("SZVTK").items);
  previewInvitation.mockResolvedValue(PREVIEW);
});

describe("signed out", () => {
  it("shows what the link is for before asking anyone to sign in", async () => {
    renderApp(`/join/${CODE}`, null);
    expect(await screen.findByRole("heading", { name: "Join Ferencváros?" })).toBeInTheDocument();
    expect(screen.getByText(/Ann Coach invited you to this team/)).toBeInTheDocument();
    expect(previewInvitation).toHaveBeenCalledWith(CODE);
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();
  });

  it("copes with a link whose inviter is unknown", async () => {
    previewInvitation.mockResolvedValue({ ...PREVIEW, invited_by_name: null });
    renderApp(`/join/${CODE}`, null);
    expect(await screen.findByText(/You've been invited to this team/)).toBeInTheDocument();
  });

  it("remembers the join page and goes to Google when signing in", async () => {
    const { auth } = renderApp(`/join/${CODE}`, null);
    await userEvent.click(
      await screen.findByRole("button", { name: "Sign in with Google to join" }),
    );
    expect(auth.mocks.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/sign-in` },
    });
    expect(sessionStorage.getItem(RETURN_KEY)).toBe(`/join/${CODE}`);
    expect(screen.getByRole("button", { name: "Sign in with Google to join" })).toBeDisabled();
  });

  it("explains a failed start and lets the visitor try again", async () => {
    const { auth } = renderApp(`/join/${CODE}`, null);
    auth.mocks.signInWithOAuth.mockResolvedValueOnce({ data: {}, error: new Error("boom") });
    await userEvent.click(
      await screen.findByRole("button", { name: "Sign in with Google to join" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("couldn't start the sign-in");
    expect(screen.getByRole("button", { name: "Sign in with Google to join" })).toBeEnabled();
  });

  it("asks the API about the link only once", async () => {
    renderApp(`/join/${CODE}`, null);
    await screen.findByRole("heading", { name: "Join Ferencváros?" });
    expect(previewInvitation).toHaveBeenCalledTimes(1);
  });

  it("does not join anyone while signed out", async () => {
    renderApp(`/join/${CODE}`, null);
    await screen.findByRole("heading", { name: "Join Ferencváros?" });
    expect(acceptInvitation).not.toHaveBeenCalled();
  });
});

describe("coming back from Google", () => {
  it("returns to the link, and the remembered code is gone from storage", async () => {
    sessionStorage.setItem(RETURN_KEY, `/join/${CODE}`);
    renderApp("/sign-in", fakeSession());
    expect(await screen.findByRole("heading", { name: "Join Ferencváros?" })).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem(RETURN_KEY)).toBeNull());
  });

  it("asks before joining: opening the link while signed in is not enough", async () => {
    renderApp(`/join/${CODE}`, fakeSession());
    expect(await screen.findByRole("button", { name: "Join team" })).toBeInTheDocument();
    expect(acceptInvitation).not.toHaveBeenCalled();
  });
});

describe("joining", () => {
  it("joins, refreshes the teams and leaves the join page without keeping it in history", async () => {
    acceptInvitation.mockImplementation(async () => {
      listTeams.mockResolvedValue(teamsPage("Ferencváros").items);
      return teamsPage("Ferencváros").items[0];
    });
    sessionStorage.setItem(RETURN_KEY, `/join/${CODE}`);
    renderApp(`/join/${CODE}`, fakeSession(), <NavigationProbe />);
    await userEvent.click(await screen.findByRole("button", { name: "Join team" }));
    expect(acceptInvitation).toHaveBeenCalledWith(CODE);
    expect(await screen.findByRole("heading", { name: "Lineup" })).toBeInTheDocument();
    expect(screen.getAllByText("Ferencváros").length).toBeGreaterThan(0);
    expect(screen.getByTestId("nav-type")).toHaveTextContent("REPLACE");
    expect(sessionStorage.getItem(RETURN_KEY)).toBeNull();
    expect(screen.queryByText(CODE, { exact: false })).not.toBeInTheDocument();
  });

  it.each([
    [410, "This invite link no longer works"],
    [404, "We don't recognise this link"],
  ])("explains a %i when joining", async (status, title) => {
    acceptInvitation.mockRejectedValue(new ApiError(status));
    renderApp(`/join/${CODE}`, fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Join team" }));
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(sessionStorage.getItem(RETURN_KEY)).toBeNull();
  });

  it("shows a generic message for any other failure and keeps the button", async () => {
    acceptInvitation.mockRejectedValue(new ApiError(500));
    renderApp(`/join/${CODE}`, fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Join team" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side");
    expect(screen.getByRole("button", { name: "Join team" })).toBeEnabled();
  });
});

describe("a link that does not work", () => {
  it.each([
    [410, "This invite link no longer works", /expired or was revoked/],
    [404, "We don't recognise this link", /whole link/],
    [422, "We don't recognise this link", /whole link/],
  ])("explains a %i on the preview", async (status, title, body) => {
    previewInvitation.mockRejectedValue(new ApiError(status));
    renderApp(`/join/${CODE}`, null);
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(body)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /join|sign in/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to the app" })).toHaveAttribute("href", "/");
  });

  it("offers a retry for a server failure instead of calling the link dead", async () => {
    previewInvitation.mockRejectedValueOnce(new ApiError(503));
    renderApp(`/join/${CODE}`, null);
    expect(await screen.findByRole("alert")).toHaveTextContent("busy or starting up");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Join Ferencváros?" })).toBeInTheDocument();
  });
});

describe("in Hungarian", () => {
  it("translates the whole page", async () => {
    renderApp(`/join/${CODE}`, null);
    await screen.findByRole("heading", { name: "Join Ferencváros?" });
    await userEvent.click(screen.getByRole("button", { name: "Magyar" }));
    expect(
      screen.getByRole("heading", { name: "Csatlakozik a(z) Ferencváros csapathoz?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Belépés Google-lal a csatlakozáshoz" }),
    ).toBeInTheDocument();
  });
});
