import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { AuthProvider } from "@/auth/provider";
import { teamsKey, type Team } from "@/features/teams/api";
import { TeamSettingsCard } from "@/features/teams/team-settings-card";
import { i18n } from "@/i18n";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ updateTeam: vi.fn() }));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  updateTeam: mocks.updateTeam,
}));

const ME = "11111111-1111-4111-8111-111111111111";
const OWNED = teamsPage("SZVTK").items[0]! as Team;

/** Renders the card for a signed-in user; `rerender` swaps the team prop like a refetch would. */
function renderCard(team: Team = OWNED) {
  const queryClient = testQueryClient();
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  const auth = fakeAuthClient(fakeSession(ME));
  const wrap = (current: Team) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={auth.client}>
        <TeamSettingsCard team={current} />
      </AuthProvider>
    </QueryClientProvider>
  );
  const view = render(wrap(team));
  return { ...view, invalidate, rerender: (next: Team) => view.rerender(wrap(next)) };
}

const nameInput = () => screen.getByRole("textbox", { name: "Team name" });
const listed = () => screen.getByRole("checkbox", { name: /opponent directory/ });
const saveButton = () => screen.getByRole("button", { name: "Save changes" });

beforeEach(() => {
  mocks.updateTeam.mockReset();
  mocks.updateTeam.mockImplementation(
    async (id: string, body: { name: string; isPublic: boolean }) => ({
      ...OWNED,
      id,
      name: body.name,
      is_public: body.isPublic,
    }),
  );
});

describe("team settings card", () => {
  it("starts from the team's current name and listing choice", () => {
    renderCard({ ...OWNED, is_public: false });
    expect(screen.getByRole("heading", { name: "Team settings" })).toBeInTheDocument();
    expect(nameInput()).toHaveValue("SZVTK");
    expect(listed()).not.toBeChecked();
    expect(screen.getByText(/Only the name is shown/)).toBeInTheDocument();
  });

  it("cannot be submitted while nothing has changed", async () => {
    renderCard();
    expect(saveButton()).toBeDisabled();
    await userEvent.type(nameInput(), "!");
    expect(saveButton()).toBeEnabled();
    await userEvent.type(nameInput(), "{Backspace}");
    expect(saveButton()).toBeDisabled();
    expect(mocks.updateTeam).not.toHaveBeenCalled();
  });

  it("saves the trimmed name and listing choice, refreshes the teams and says so", async () => {
    const { invalidate } = renderCard();
    await userEvent.clear(nameInput());
    await userEvent.type(nameInput(), "  SZVTK II  ");
    await userEvent.click(listed());
    await userEvent.click(saveButton());
    expect(mocks.updateTeam).toHaveBeenCalledWith(OWNED.id, { name: "SZVTK II", isPublic: false });
    expect(await screen.findByRole("status")).toHaveTextContent("Saved.");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: teamsKey(ME) });
    expect(nameInput()).toHaveValue("SZVTK II");
    expect(saveButton()).toBeDisabled();
  });

  it("hides the saved message again once the form is edited", async () => {
    renderCard();
    await userEvent.type(nameInput(), " II");
    await userEvent.click(saveButton());
    await screen.findByRole("status");
    await userEvent.type(nameInput(), "I");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("follows the team when the refreshed values arrive", () => {
    const { rerender } = renderCard();
    rerender({ ...OWNED, name: "Renamed elsewhere", is_public: false });
    expect(nameInput()).toHaveValue("Renamed elsewhere");
    expect(listed()).not.toBeChecked();
    expect(saveButton()).toBeDisabled();
  });

  it("checks the name before sending anything", async () => {
    renderCard();
    await userEvent.clear(nameInput());
    await userEvent.click(saveButton());
    expect(await screen.findByText("Team name is required")).toBeInTheDocument();
    expect(mocks.updateTeam).not.toHaveBeenCalled();
  });

  it("puts the server's 422 message next to the name", async () => {
    mocks.updateTeam.mockRejectedValue(
      new ApiError(422, { detail: [{ loc: ["body", "name"], msg: "Value error, Name is taken" }] }),
    );
    renderCard();
    await userEvent.type(nameInput(), " II");
    await userEvent.click(saveButton());
    expect(await screen.findByText("Name is taken")).toBeInTheDocument();
    expect(nameInput()).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("explains a refusal in plain words, without the server's text", async () => {
    mocks.updateTeam.mockRejectedValue(new ApiError(403, { detail: "Owner role required" }));
    const { invalidate } = renderCard();
    await userEvent.type(nameInput(), " II");
    await userEvent.click(saveButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("don't have permission");
    expect(document.body.textContent).not.toContain("Owner role required");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("renders nothing for a member", () => {
    const { container } = renderCard({ ...OWNED, role: "member" });
    expect(container).toBeEmptyDOMElement();
  });

  it("speaks Hungarian", async () => {
    renderCard();
    await act(() => i18n.changeLanguage("hu"));
    try {
      expect(
        await screen.findByRole("heading", { name: "Csapat beállításai" }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Módosítások mentése" })).toBeDisabled();
    } finally {
      await act(() => i18n.changeLanguage("en"));
    }
  });
});
