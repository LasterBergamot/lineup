import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { UseQueryResult } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { Team } from "@/features/teams/api";
import { TeamsContext } from "@/features/teams/context";
import { RosterPage } from "@/pages/roster-page";
import { fakeSession, renderApp, teamsPage } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listTeams: vi.fn(),
  listPlayers: vi.fn(),
  createPlayer: vi.fn(),
  searchPool: vi.fn(),
  listStaff: vi.fn(),
}));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams: mocks.listTeams,
}));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  listPlayers: mocks.listPlayers,
  createPlayer: mocks.createPlayer,
}));
vi.mock("@/features/staff/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff/api")>()),
  listStaff: mocks.listStaff,
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
  mocks.listStaff.mockResolvedValue([]);
});

describe("roster page", () => {
  it("shows the team's players, its settings and the opponent directory to an owner", async () => {
    renderApp("/roster", fakeSession());
    expect(await screen.findByRole("heading", { name: "Roster" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Edit Kovács Béla" })).toBeInTheDocument();
    expect(mocks.listPlayers).toHaveBeenCalledWith(TEAM);
    expect(await screen.findByRole("heading", { name: "Staff" })).toBeInTheDocument();
    expect(mocks.listStaff).toHaveBeenCalledWith(TEAM);
    expect(await screen.findByRole("heading", { name: "Team settings" })).toBeInTheDocument();
    expect(await screen.findByText("FTC")).toBeInTheDocument();
  });

  it("hides the team settings from a member, who can still edit the roster", async () => {
    asMember();
    renderApp("/roster", fakeSession());
    expect(await screen.findByRole("button", { name: "Edit Kovács Béla" })).toBeInTheDocument();
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

describe("roster page with unsaved changes", () => {
  const sidebarLink = async (name: string) =>
    within(await screen.findByRole("navigation", { name: "Sidebar" })).getByRole("link", { name });
  const addForm = () => screen.getByRole("form", { name: "Add a player" });

  /** Fires `beforeunload` the way a reload would and says whether the page asked to stay. */
  function reloadIsHeld() {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  }

  it("asks before the navigation drops a typed-in player: Stay keeps it, Discard leaves", async () => {
    const user = userEvent.setup();
    renderApp("/roster", fakeSession());
    await screen.findByRole("button", { name: "Edit Kovács Béla" });
    await user.type(within(addForm()).getByLabelText("Name"), "Nagy Péter");
    expect(reloadIsHeld()).toBe(true);

    await user.click(await sidebarLink("Lineup"));
    const dialog = await screen.findByRole("dialog", { name: "Discard changes?" });
    await user.click(within(dialog).getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Roster" })).toBeInTheDocument();
    expect(within(addForm()).getByLabelText("Name")).toHaveValue("Nagy Péter");

    await user.click(await sidebarLink("Lineup"));
    await user.click(await screen.findByRole("button", { name: "Discard" }));
    expect(await screen.findByRole("heading", { name: "Lineup" })).toBeInTheDocument();
    expect(reloadIsHeld()).toBe(false);
  });

  it("does not ask once the player is saved", async () => {
    mocks.createPlayer.mockResolvedValue({});
    const user = userEvent.setup();
    renderApp("/roster", fakeSession());
    await screen.findByRole("button", { name: "Edit Kovács Béla" });
    await user.type(within(addForm()).getByLabelText("Name"), "Nagy Péter");
    await user.type(within(addForm()).getByLabelText("NSSZ number"), "HUN-2");
    await user.click(within(addForm()).getByRole("button", { name: "Add player" }));
    await vi.waitFor(() => expect(within(addForm()).getByLabelText("Name")).toHaveValue(""));
    expect(reloadIsHeld()).toBe(false);
    await user.click(await sidebarLink("Saved"));
    expect(await screen.findByRole("heading", { name: "Saved lineups" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("guards an unsaved team rename and an open player edit", async () => {
    const user = userEvent.setup();
    renderApp("/roster", fakeSession());
    await screen.findByRole("button", { name: "Edit Kovács Béla" });
    const teamName = await screen.findByLabelText("Team name");
    await user.type(teamName, " II");
    expect(reloadIsHeld()).toBe(true);
    await user.clear(teamName);
    await user.type(teamName, "SZVTK");
    expect(reloadIsHeld()).toBe(false);

    await user.click(screen.getByRole("button", { name: "Edit Kovács Béla" }));
    const edit = screen.getByRole("form", { name: "Edit Kovács Béla" });
    await user.type(within(edit).getByLabelText("Name"), "!");
    expect(reloadIsHeld()).toBe(true);
    await user.click(within(edit).getByRole("button", { name: "Cancel" }));
    expect(reloadIsHeld()).toBe(false);
  });

  it("never keeps a user who signs out on the page", async () => {
    const user = userEvent.setup();
    renderApp("/roster", fakeSession());
    await screen.findByRole("button", { name: "Edit Kovács Béla" });
    await user.type(within(addForm()).getByLabelText("Name"), "Nagy Péter");
    const sidebar = screen.getByRole("complementary");
    await user.click(within(sidebar).getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(reloadIsHeld()).toBe(false);
  });
});

describe("roster page without a current team", () => {
  it("renders nothing (the team gate normally keeps this from happening)", () => {
    const query = { data: [] } as unknown as UseQueryResult<Team[]>;
    const { container } = render(
      <TeamsContext.Provider value={{ query, current: undefined }}>
        <RosterPage />
      </TeamsContext.Provider>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
