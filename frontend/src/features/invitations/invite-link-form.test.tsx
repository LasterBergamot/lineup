import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fakeSession, renderApp } from "@/test/auth";

const { listTeams, previewInvitation } = vi.hoisted(() => ({
  listTeams: vi.fn(),
  previewInvitation: vi.fn(),
}));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams,
}));
vi.mock("@/features/invitations/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/invitations/api")>()),
  previewInvitation,
}));

beforeEach(() => {
  listTeams.mockReset();
  previewInvitation.mockReset();
  listTeams.mockResolvedValue([]);
  previewInvitation.mockResolvedValue({
    team_name: "Ferencváros",
    invited_by_name: null,
    expires_at: "2026-11-01T10:00:00",
  });
});

describe("pasting an invite link on the onboarding screen", () => {
  it("opens the join page for the pasted link", async () => {
    renderApp("/", fakeSession());
    await userEvent.type(
      await screen.findByLabelText("Invite link"),
      "https://x.example/join/abc_-9",
    );
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByRole("heading", { name: "Join Ferencváros?" })).toBeInTheDocument();
    expect(previewInvitation).toHaveBeenCalledWith("abc_-9");
  });

  it("also takes the bare code", async () => {
    renderApp("/", fakeSession());
    await userEvent.type(await screen.findByLabelText("Invite link"), "  abc123  ");
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    await screen.findByRole("heading", { name: "Join Ferencváros?" });
    expect(previewInvitation).toHaveBeenCalledWith("abc123");
  });

  it.each([
    ["", "Invite link is required"],
    ["not a link", "That doesn't look like an invite link"],
  ])("rejects %j before leaving the page", async (value, message) => {
    renderApp("/", fakeSession());
    const field = await screen.findByLabelText("Invite link");
    if (value) await userEvent.type(field, value);
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(previewInvitation).not.toHaveBeenCalled();
  });
});
