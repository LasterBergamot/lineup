import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { fakeSession, membersList, renderApp, teamsPage } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listTeams: vi.fn(),
  listMembers: vi.fn(),
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
}));
vi.mock("@/features/invitations/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/invitations/api")>()),
  listInvitations: mocks.listInvitations,
  createInvitation: mocks.createInvitation,
  revokeInvitation: mocks.revokeInvitation,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";
const URL_ = "https://lineup-kfi.pages.dev/join/SECRETCODE";
const CREATED = {
  id: "i-new",
  code: "SECRETCODE",
  url: URL_,
  role: "member",
  expires_at: "2026-11-01T10:00:00",
};
const ACTIVE = [
  {
    id: "i-1",
    role: "member",
    created_at: "2026-10-31T09:00:00",
    expires_at: "2026-11-01T09:00:00",
  },
  {
    id: "i-2",
    role: "member",
    created_at: "2026-10-30T09:00:00",
    expires_at: "2026-11-02T09:00:00",
  },
];

async function open() {
  renderApp("/members", fakeSession());
  return screen.findByRole("heading", { name: "Invite people" });
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listTeams.mockResolvedValue(teamsPage("SZVTK").items);
  mocks.listMembers.mockResolvedValue(membersList());
  mocks.listInvitations.mockResolvedValue([]);
  mocks.createInvitation.mockResolvedValue(CREATED);
  mocks.revokeInvitation.mockResolvedValue(undefined);
});

afterEach(() => {
  Reflect.deleteProperty(navigator, "share");
  Reflect.deleteProperty(navigator, "clipboard");
  sessionStorage.clear();
});

describe("creating a link", () => {
  it("asks for 24 hours by default and shows the link once, with its expiry", async () => {
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    expect(mocks.createInvitation).toHaveBeenCalledWith(TEAM, 24);
    expect(await screen.findByLabelText("Your invite link")).toHaveValue(URL_);
    expect(screen.getByText(/shown only here, only once/)).toBeInTheDocument();
    await waitFor(() => expect(mocks.listInvitations).toHaveBeenCalledTimes(2));
  });

  it("offers 2 hours, 24 hours and 3 days", async () => {
    await open();
    const choice = screen.getByLabelText("Link valid for");
    expect(
      within(choice)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["2 hours", "24 hours", "3 days"]);
    await userEvent.selectOptions(choice, "3 days");
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    expect(mocks.createInvitation).toHaveBeenCalledWith(TEAM, 72);
  });

  it("never writes the link or its code to browser storage", async () => {
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    await screen.findByLabelText("Your invite link");
    const stored = JSON.stringify({ ...localStorage, ...sessionStorage });
    expect(stored).not.toContain("SECRETCODE");
  });

  it("shows a generic message when it fails", async () => {
    mocks.createInvitation.mockRejectedValue(new ApiError(429));
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side");
  });
});

describe("copying and sharing", () => {
  async function created() {
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    await screen.findByLabelText("Your invite link");
  }

  it("copies the link", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await created();
    await userEvent.click(screen.getByRole("button", { name: "Copy link" }));
    expect(writeText).toHaveBeenCalledWith(URL_);
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
  });

  it("tells the owner to copy by hand when the browser refuses", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
      configurable: true,
    });
    await created();
    await userEvent.click(screen.getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText(/Couldn't copy/)).toBeInTheDocument();
  });

  it("selects the whole link when the field gets focus, so it can be copied by hand", async () => {
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    const field = (await screen.findByLabelText("Your invite link")) as HTMLInputElement;
    await userEvent.click(field);
    expect(field.selectionStart).toBe(0);
    expect(field.selectionEnd).toBe(URL_.length);
  });

  it("has no Share button where the browser cannot share", async () => {
    await created();
    expect(screen.queryByRole("button", { name: "Share" })).not.toBeInTheDocument();
  });

  it("opens the share sheet where there is one, and ignores it being closed", async () => {
    const share = vi.fn().mockRejectedValue(new DOMException("closed", "AbortError"));
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    await created();
    await userEvent.click(screen.getByRole("button", { name: "Share" }));
    expect(share).toHaveBeenCalledWith({ title: "Join SZVTK on Lineup", url: URL_ });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("active links", () => {
  it("lists them with their expiry", async () => {
    mocks.listInvitations.mockResolvedValue(ACTIVE);
    await open();
    expect(await screen.findAllByText(/^Created .*, expires /)).toHaveLength(2);
  });

  it("revokes one after confirming, and stops showing a link that was just revoked", async () => {
    mocks.listInvitations.mockResolvedValue([{ ...ACTIVE[0]!, id: "i-new" }]);
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    await screen.findByLabelText("Your invite link");
    await userEvent.click(await screen.findByRole("button", { name: "Revoke" }));
    expect(mocks.revokeInvitation).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Yes, revoke" }));
    expect(mocks.revokeInvitation).toHaveBeenCalledWith(TEAM, "i-new");
    await waitFor(() =>
      expect(screen.queryByLabelText("Your invite link")).not.toBeInTheDocument(),
    );
  });

  it("keeps the link on screen when a different one is revoked", async () => {
    mocks.listInvitations.mockResolvedValue(ACTIVE);
    await open();
    await userEvent.click(screen.getByRole("button", { name: "Create invite link" }));
    await screen.findByLabelText("Your invite link");
    await userEvent.click((await screen.findAllByRole("button", { name: "Revoke" }))[0]!);
    await userEvent.click(screen.getByRole("button", { name: "Yes, revoke" }));
    await waitFor(() => expect(mocks.revokeInvitation).toHaveBeenCalledWith(TEAM, "i-1"));
    expect(screen.getByLabelText("Your invite link")).toBeInTheDocument();
  });

  it("explains a failed revoke", async () => {
    mocks.listInvitations.mockResolvedValue(ACTIVE);
    mocks.revokeInvitation.mockRejectedValue(new ApiError(404));
    await open();
    await userEvent.click((await screen.findAllByRole("button", { name: "Revoke" }))[0]!);
    await userEvent.click(screen.getByRole("button", { name: "Yes, revoke" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no longer exists");
  });
});
