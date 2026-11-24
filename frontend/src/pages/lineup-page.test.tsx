import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Fragment, type ComponentType, type ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { ToastProvider } from "@/components/ui/toast";
import type { Player } from "@/features/players/api";
import type { Team } from "@/features/teams/api";
import { TeamsContext } from "@/features/teams/context";
import { LineupPage } from "@/pages/lineup-page";
import { unsavedProbe } from "@/test/unsaved";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ listPlayers: vi.fn(), getSavedLineup: vi.fn() }));
vi.mock("@/features/creator/api", () => ({ getSavedLineup: mocks.getSavedLineup }));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  listPlayers: mocks.listPlayers,
}));
// Both forms have their own tests; here only what the page hands them and what survives a mode
// switch matter. Each stand-in keeps one typed value in state and reports it to the guard.
vi.mock("@/features/creator/lineup-creator", async () => {
  const { useState } = await import("react");
  const { useUnsavedChangesGuard } = await import("@/lib/unsaved-changes");
  return {
    LineupCreator: ({
      roster,
      initialValues,
    }: {
      roster: Player[];
      initialValues?: { division: string; players: { name: string }[] };
    }) => {
      const [typed, setTyped] = useState("");
      useUnsavedChangesGuard(typed !== "");
      return (
        <div>
          <p>
            creator: {roster.length} players, division {initialValues?.division ?? "none"},{" "}
            {initialValues?.players.map((p) => p.name).join("+")}
          </p>
          <input
            aria-label="creator field"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        </div>
      );
    },
  };
});
vi.mock("@/features/lineup/lineup-form", async () => {
  const { useState } = await import("react");
  const { useUnsavedChangesGuard } = await import("@/lib/unsaved-changes");
  return {
    LineupForm: () => {
      const [typed, setTyped] = useState("");
      useUnsavedChangesGuard(typed !== "");
      return (
        <div>
          <p>quick sheet form</p>
          <input
            aria-label="quick field"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
          />
        </div>
      );
    },
  };
});

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

function renderPage(
  state?: unknown,
  current: Team | null = team,
  Wrapper: ComponentType<{ children: ReactNode }> = Fragment,
) {
  render(
    <QueryClientProvider client={testQueryClient()}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <ToastProvider>
          <MemoryRouter initialEntries={[{ pathname: "/", state }]}>
            <Wrapper>
              <SignedIn current={current ?? undefined} />
            </Wrapper>
          </MemoryRouter>
        </ToastProvider>
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
    expect(screen.getByRole("tab", { name: "From the roster" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tabpanel", { name: "From the roster" })).toBeInTheDocument();
  });

  it("switches to the quick sheet and back, hiding the mode that is not shown", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/creator:/);
    expect(screen.getByText("quick sheet form")).not.toBeVisible();
    await user.click(screen.getByRole("tab", { name: "Quick sheet (not saved)" }));
    expect(screen.getByText("quick sheet form")).toBeVisible();
    expect(screen.getByText(/creator:/)).not.toBeVisible();
    expect(screen.getByText(/Nothing is saved/)).toBeInTheDocument();
    expect(screen.getByRole("tabpanel", { name: "Quick sheet (not saved)" })).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "From the roster" }));
    expect(screen.getByText(/creator:/)).toBeVisible();
    expect(screen.getByText("quick sheet form")).not.toBeVisible();
  });

  it("keeps what was typed in either mode across a switch", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/creator:/);
    await user.type(screen.getByLabelText("creator field"), "Anna");
    await user.click(screen.getByRole("tab", { name: "Quick sheet (not saved)" }));
    await user.type(screen.getByLabelText("quick field"), "Béla");
    await user.click(screen.getByRole("tab", { name: "From the roster" }));
    expect(screen.getByLabelText("creator field")).toHaveValue("Anna");
    await user.click(screen.getByRole("tab", { name: "Quick sheet (not saved)" }));
    expect(screen.getByLabelText("quick field")).toHaveValue("Béla");
  });

  it("keeps reporting unsaved input to the guard from the hidden mode", async () => {
    const user = userEvent.setup();
    const probe = unsavedProbe();
    renderPage(undefined, team, probe.Wrapper);
    await screen.findByText(/creator:/);
    expect(probe.isDirty()).toBe(false);
    await user.type(screen.getByLabelText("creator field"), "A");
    await user.click(screen.getByRole("tab", { name: "Quick sheet (not saved)" }));
    expect(probe.isDirty()).toBe(true);
    await user.click(screen.getByRole("tab", { name: "From the roster" }));
    await user.clear(screen.getByLabelText("creator field"));
    expect(probe.isDirty()).toBe(false);
    await user.type(screen.getByLabelText("creator field"), "A");
    await user.click(screen.getByRole("tab", { name: "Quick sheet (not saved)" }));
    await user.type(screen.getByLabelText("quick field"), "B");
    await user.click(screen.getByRole("tab", { name: "From the roster" }));
    expect(probe.isDirty()).toBe(true);
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
