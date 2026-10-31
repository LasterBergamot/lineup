import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import type { Player } from "@/features/players/api";
import type { Team } from "@/features/teams/api";
import { TeamsContext } from "@/features/teams/context";
import { LineupPage } from "@/pages/lineup-page";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ listPlayers: vi.fn(), getSavedLineup: vi.fn() }));
vi.mock("@/features/creator/api", () => ({ getSavedLineup: mocks.getSavedLineup }));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  listPlayers: mocks.listPlayers,
}));
// Both forms have their own tests; here only what the page hands them matters.
vi.mock("@/features/creator/lineup-creator", () => ({
  LineupCreator: ({
    roster,
    initialValues,
  }: {
    roster: Player[];
    initialValues?: { division: string; players: { name: string }[] };
  }) => (
    <p>
      creator: {roster.length} players, division {initialValues?.division ?? "none"},{" "}
      {initialValues?.players.map((p) => p.name).join("+")}
    </p>
  ),
}));
vi.mock("@/features/lineup/lineup-form", () => ({ LineupForm: () => <p>quick sheet form</p> }));

const team = { ...teamsPage("SZVTK").items[0]!, id: "t-1" } as Team;
const ANN: Player = {
  id: "p-ann",
  team_id: "t-1",
  name: "Kovács Anna",
  nssz_number: "N1",
  created_at: "",
};
const SAVED = {
  id: "s-1",
  division: "OB I.",
  cap: "Kék",
  coach: "Edző",
  doctor: null,
  assistant_coach: null,
  team_leader: null,
  ball_thrower: null,
  players: [
    { id: "x", cap_number: 1, name: "Kovács Anna", nssz_number: "N1", source_player_id: "p-ann" },
  ],
};

function SignedIn({ current }: { current: Team | undefined }) {
  const auth = useAuth();
  if (auth.status !== "signed-in") return null;
  return (
    <TeamsContext.Provider value={{ query: {} as never, current }}>
      <LineupPage />
    </TeamsContext.Provider>
  );
}

function renderPage(state?: unknown, current: Team | null = team) {
  render(
    <QueryClientProvider client={testQueryClient()}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <MemoryRouter initialEntries={[{ pathname: "/", state }]}>
          <SignedIn current={current ?? undefined} />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mocks.listPlayers.mockReset();
  mocks.getSavedLineup.mockReset();
  mocks.listPlayers.mockResolvedValue([ANN]);
  mocks.getSavedLineup.mockResolvedValue(SAVED);
});

describe("LineupPage", () => {
  it("loads the roster, then shows the creator", async () => {
    renderPage();
    expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByText(/creator: 1 players, division none/)).toBeInTheDocument();
    expect(mocks.listPlayers).toHaveBeenCalledWith("t-1");
    expect(screen.getByRole("heading", { name: "Lineup" })).toBeInTheDocument();
    expect(screen.getByText(/Build the lineup for SZVTK/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "From the roster" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("switches to the quick sheet and back", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/creator:/);
    await user.click(screen.getByRole("button", { name: "Quick sheet (not saved)" }));
    expect(screen.getByText("quick sheet form")).toBeInTheDocument();
    expect(screen.queryByText(/creator:/)).not.toBeInTheDocument();
    expect(screen.getByText(/Nothing is saved/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "From the roster" }));
    expect(await screen.findByText(/creator:/)).toBeInTheDocument();
  });

  it("fetches the lineup to clone by its id and starts the creator from it", async () => {
    renderPage({ cloneFromId: "s-1" });
    expect(await screen.findByText(/division OB I\., Kovács Anna/)).toBeInTheDocument();
    expect(mocks.getSavedLineup).toHaveBeenCalledWith("s-1");
  });

  it("shows a retry when the lineup to clone cannot be loaded", async () => {
    mocks.getSavedLineup.mockRejectedValueOnce(new ApiError(404));
    renderPage({ cloneFromId: "s-1" });
    expect(await screen.findByText(/no longer exists/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/division OB I\./)).toBeInTheDocument();
  });

  it("ignores navigation state that is not a lineup id", async () => {
    renderPage({ cloneFromId: 7 });
    expect(await screen.findByText(/division none/)).toBeInTheDocument();
    expect(mocks.getSavedLineup).not.toHaveBeenCalled();
  });

  it("offers a retry when the roster cannot be loaded", async () => {
    mocks.listPlayers.mockRejectedValueOnce(new ApiError(503));
    renderPage();
    expect(await screen.findByText(/busy or starting up/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText(/creator:/)).toBeInTheDocument();
  });

  it("renders nothing without a current team (TeamGate normally prevents it)", () => {
    renderPage(undefined, null);
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(mocks.listPlayers).not.toHaveBeenCalled();
  });
});
