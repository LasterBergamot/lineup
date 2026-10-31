import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fakeSession, renderApp, teamsPage } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listTeams: vi.fn(),
  listPlayers: vi.fn(),
  searchPool: vi.fn(),
}));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams: mocks.listTeams,
}));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  listPlayers: mocks.listPlayers,
}));
vi.mock("@/features/directory/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/directory/api")>()),
  searchPool: mocks.searchPool,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";

function asMember() {
  mocks.listTeams.mockResolvedValue(
    teamsPage("SZVTK").items.map((team) => ({ ...team, role: "member" })),
  );
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listTeams.mockResolvedValue(teamsPage("SZVTK").items);
  mocks.listPlayers.mockResolvedValue([
    {
      id: "44444444-4444-4444-8444-444444444444",
      name: "Kovács Béla",
      nssz_number: "HUN-1",
      team_id: TEAM,
      created_at: "2026-10-05T10:00:00",
    },
  ]);
  mocks.searchPool.mockResolvedValue([{ id: "55555555-5555-4555-8555-555555555555", name: "FTC" }]);
});

describe("roster page", () => {
  it("shows the team's players, its settings and the opponent directory to an owner", async () => {
    renderApp("/roster", fakeSession());
    expect(await screen.findByRole("heading", { name: "Roster" })).toBeInTheDocument();
    expect(await screen.findByText("Kovács Béla")).toBeInTheDocument();
    expect(mocks.listPlayers).toHaveBeenCalledWith(TEAM);
    expect(await screen.findByRole("heading", { name: "Team settings" })).toBeInTheDocument();
    expect(await screen.findByText("FTC")).toBeInTheDocument();
  });

  it("hides the team settings from a member, who can still edit the roster", async () => {
    asMember();
    renderApp("/roster", fakeSession());
    expect(await screen.findByText("Kovács Béla")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Kovács Béla" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Team settings" })).not.toBeInTheDocument();
  });

  it("is reachable from the navigation", async () => {
    renderApp("/", fakeSession());
    await userEvent.click(
      within(await screen.findByRole("navigation", { name: "Sidebar" })).getByRole("link", {
        name: "Roster",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Roster" })).toBeInTheDocument();
  });
});
