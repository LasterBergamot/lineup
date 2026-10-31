import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { fakeSession, membersList, renderApp, teamsPage } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listTeams: vi.fn(),
  listMembers: vi.fn(),
  removeMember: vi.fn(),
  transferOwnership: vi.fn(),
  listInvitations: vi.fn(),
  createInvitation: vi.fn(),
  revokeInvitation: vi.fn(),
}));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams: mocks.listTeams,
}));
vi.mock("@/features/members/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/members/api")>()),
  listMembers: mocks.listMembers,
  removeMember: mocks.removeMember,
  transferOwnership: mocks.transferOwnership,
}));
vi.mock("@/features/invitations/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/invitations/api")>()),
  listInvitations: mocks.listInvitations,
  createInvitation: mocks.createInvitation,
  revokeInvitation: mocks.revokeInvitation,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";
const ME = "11111111-1111-4111-8111-111111111111";
const ANN = "22222222-2222-4222-8222-222222222222";
const BEN = "33333333-3333-4333-8333-333333333333";

function asMember() {
  mocks.listTeams.mockResolvedValue(
    teamsPage("SZVTK").items.map((team) => ({ ...team, role: "member" })),
  );
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listTeams.mockResolvedValue(teamsPage("SZVTK").items);
  mocks.listMembers.mockResolvedValue(membersList({ id: ANN }, { id: BEN }));
  mocks.listInvitations.mockResolvedValue([]);
  mocks.removeMember.mockResolvedValue(undefined);
  mocks.revokeInvitation.mockResolvedValue(undefined);
});

describe("members list", () => {
  it("shows people as You and Member N, with roles and no user ids", async () => {
    renderApp("/members", fakeSession());
    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
    const rows = await screen.findAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("You"),
      expect.stringContaining("Member 1"),
      expect.stringContaining("Member 2"),
    ]);
    expect(within(rows[0]!).getByText("owner")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("member")).toBeInTheDocument();
    expect(mocks.listMembers).toHaveBeenCalledWith(TEAM);
    for (const id of [ME, ANN, BEN]) expect(document.body.textContent).not.toContain(id);
  });

  it("is reachable from the navigation", async () => {
    renderApp("/", fakeSession());
    await userEvent.click(
      within(await screen.findByRole("navigation", { name: "Sidebar" })).getByRole("link", {
        name: "Team",
      }),
    );
    expect(await screen.findByRole("heading", { name: "Team" })).toBeInTheDocument();
  });

  it("offers a retry when the list cannot be loaded", async () => {
    mocks.listMembers.mockRejectedValueOnce(new ApiError(503));
    renderApp("/members", fakeSession());
    expect(await screen.findByText(/busy or starting up/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Member 1")).toBeInTheDocument();
  });

  it("speaks Hungarian", async () => {
    renderApp("/members", fakeSession());
    await screen.findByText("Member 2");
    await userEvent.click(screen.getAllByRole("button", { name: "Magyar" })[0]!);
    expect(await screen.findByText("2. tag")).toBeInTheDocument();
    expect(screen.getByText("Ön")).toBeInTheDocument();
  });
});

describe("as an owner", () => {
  it("removes a member only after confirming", async () => {
    renderApp("/members", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Remove member 1" }));
    expect(mocks.removeMember).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Yes, remove" }));
    expect(mocks.removeMember).toHaveBeenCalledWith(TEAM, ANN);
    await waitFor(() => expect(mocks.listMembers).toHaveBeenCalledTimes(2));
  });

  it("hands the team over, then reloads the teams so the new role shows", async () => {
    mocks.transferOwnership.mockResolvedValue(teamsPage("SZVTK").items[0]);
    renderApp("/members", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Make member 2 the owner" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, make owner" }));
    expect(mocks.transferOwnership).toHaveBeenCalledWith(TEAM, BEN);
    await waitFor(() => expect(mocks.listTeams).toHaveBeenCalledTimes(2));
  });

  it("explains a refusal in plain words and refreshes the list", async () => {
    mocks.removeMember.mockRejectedValue(new ApiError(403));
    renderApp("/members", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Remove member 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, remove" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("don't have permission");
    expect(mocks.listMembers).toHaveBeenCalledTimes(2);
  });

  it("shows the invite tools", async () => {
    renderApp("/members", fakeSession());
    expect(await screen.findByRole("heading", { name: "Invite people" })).toBeInTheDocument();
    expect(await screen.findByText("No active invite links.")).toBeInTheDocument();
  });
});

describe("as a member", () => {
  beforeEach(asMember);

  it("sees the list and can leave, but has no owner controls", async () => {
    renderApp("/members", fakeSession());
    await screen.findByText("Member 1");
    expect(screen.getByRole("button", { name: "Leave team" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Remove/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Make member/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Invite people" })).not.toBeInTheDocument();
    expect(mocks.listInvitations).not.toHaveBeenCalled();
  });
});

describe("leaving", () => {
  it("leaves with the caller's own id and lands on onboarding with no team left", async () => {
    mocks.removeMember.mockImplementation(async () => {
      mocks.listTeams.mockResolvedValue([]);
    });
    renderApp("/members", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Leave team" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, leave" }));
    expect(mocks.removeMember).toHaveBeenCalledWith(TEAM, ME);
    expect(await screen.findByRole("heading", { name: "Welcome to Lineup" })).toBeInTheDocument();
  });

  it("says why the only owner cannot leave", async () => {
    mocks.removeMember.mockRejectedValue(new ApiError(409));
    renderApp("/members", fakeSession());
    await userEvent.click(await screen.findByRole("button", { name: "Leave team" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, leave" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("only owner");
  });
});
