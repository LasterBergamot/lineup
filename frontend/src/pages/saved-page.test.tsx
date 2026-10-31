import type { UseQueryResult } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Team } from "@/features/teams/api";
import { TeamsContext } from "@/features/teams/context";
import { SavedPage } from "@/pages/saved-page";
import { fakeSession, renderApp, teamsPage } from "@/test/auth";

const mocks = vi.hoisted(() => ({ listTeams: vi.fn(), listSavedLineups: vi.fn() }));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams: mocks.listTeams,
}));
vi.mock("@/features/saved/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/saved/api")>()),
  listSavedLineups: mocks.listSavedLineups,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listTeams.mockResolvedValue(teamsPage("SZVTK").items);
  mocks.listSavedLineups.mockResolvedValue([
    {
      id: "l-1",
      team_id: TEAM,
      team_name: "SZVTK",
      opponent_name: "FTC",
      match_name: "SZVTK - FTC",
      division: "OB II.",
      cap: "Fehér",
      date: "2026. 10. 31.",
      coach: "Coach",
      doctor: null,
      assistant_coach: null,
      team_leader: null,
      ball_thrower: null,
      source_team_id: TEAM,
      source_opponent_id: null,
      players: [],
      created_at: "2026-10-31T10:00:00",
    },
  ]);
});

describe("saved page", () => {
  it("lists the current team's saved lineups", async () => {
    renderApp("/saved", fakeSession());
    expect(await screen.findByRole("heading", { name: "Saved lineups" })).toBeInTheDocument();
    expect(await screen.findByText("SZVTK - FTC")).toBeInTheDocument();
    expect(mocks.listSavedLineups).toHaveBeenCalledWith(TEAM);
  });

  it("is reachable from the navigation", async () => {
    renderApp("/", fakeSession());
    const nav = await screen.findByRole("navigation", { name: "Sidebar" });
    await userEvent.click(within(nav).getByRole("link", { name: "Saved" }));
    expect(await screen.findByText("SZVTK - FTC")).toBeInTheDocument();
  });

  it("renders nothing without a current team (TeamGate normally prevents that)", () => {
    const value = { query: {} as UseQueryResult<Team[]>, current: undefined };
    const { container } = render(
      <TeamsContext.Provider value={value}>
        <SavedPage />
      </TeamsContext.Provider>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
