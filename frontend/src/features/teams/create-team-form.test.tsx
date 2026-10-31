import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { CreateTeamForm } from "@/features/teams/create-team-form";
import { fakeAuthClient, fakeSession, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ createTeam: vi.fn() }));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  createTeam: mocks.createTeam,
}));

/** Renders the form once the fake session is in, as `RequireAuth` does in the app. */
function SignedIn() {
  return useAuth().status === "signed-in" ? <CreateTeamForm /> : null;
}

function renderForm() {
  render(
    <QueryClientProvider client={testQueryClient()}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <SignedIn />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mocks.createTeam.mockReset();
});

describe("create team form", () => {
  it("shows the generic message for a 422 about a field the form does not show", async () => {
    mocks.createTeam.mockImplementation(async () => {
      throw new ApiError(422, {
        detail: [{ loc: ["body", "is_public"], msg: "Value error, odd" }],
      });
    });
    renderForm();
    const name = await screen.findByLabelText("Team name");
    await userEvent.type(name, "SZVTK");
    await userEvent.click(screen.getByRole("button", { name: "Create team" }));
    await waitFor(() => expect(mocks.createTeam).toHaveBeenCalledOnce());
    await waitFor(() => expect(screen.getByRole("button", { name: "Create team" })).toBeEnabled());
    expect(await screen.findByRole("alert")).toHaveTextContent("rejected");
    expect(name).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByText("odd")).not.toBeInTheDocument();
  });
});
