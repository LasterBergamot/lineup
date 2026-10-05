import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach } from "vitest";
import { fakeSession, renderApp, teamsPage } from "@/test/auth";

const { listTeams } = vi.hoisted(() => ({ listTeams: vi.fn() }));
vi.mock("@/features/teams/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/teams/api")>()),
  listTeams,
}));

async function renderAt(path: string) {
  const view = renderApp(path, fakeSession());
  // The shell renders at once; the page appears once the team list has loaded.
  await screen.findAllByText("SZVTK");
  return view;
}

beforeEach(() => {
  listTeams.mockReset();
  listTeams.mockResolvedValue(teamsPage("SZVTK").items);
});

describe("AppShell", () => {
  it("shows the same three destinations in the sidebar and the bottom bar", async () => {
    await renderAt("/");
    for (const name of ["Sidebar", "Bottom"]) {
      const nav = screen.getByRole("navigation", { name });
      expect(
        within(nav)
          .getAllByRole("link")
          .map((a) => a.textContent),
      ).toEqual(["Lineup", "Roster", "Saved"]);
    }
  });

  it("renders the routed page inside the shell and marks the active link", async () => {
    await renderAt("/roster");
    expect(screen.getByRole("heading", { name: "Roster" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Sidebar" });
    expect(within(nav).getByRole("link", { name: "Roster" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Lineup" })).not.toHaveAttribute("aria-current");
  });

  it("navigates between pages", async () => {
    await renderAt("/");
    await userEvent.click(
      within(screen.getByRole("navigation", { name: "Bottom" })).getByRole("link", {
        name: "Saved",
      }),
    );
    expect(screen.getByRole("heading", { name: "Saved lineups" })).toBeInTheDocument();
  });

  it("shows a not-found page for unknown addresses", async () => {
    await renderAt("/nope");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("toggles the dark theme and remembers it", async () => {
    await renderAt("/");
    const [toggle] = screen.getAllByRole("button", { name: "Switch to dark theme" });
    await userEvent.click(toggle!);
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("lineup-theme")).toBe("dark");
    await userEvent.click(screen.getAllByRole("button", { name: "Switch to light theme" })[0]!);
    expect(document.documentElement).not.toHaveClass("dark");
    expect(localStorage.getItem("lineup-theme")).toBe("light");
  });

  it("shows the current team and the caller's role, and loads the teams once", async () => {
    await renderAt("/");
    const sidebar = screen.getByRole("complementary");
    expect(within(sidebar).getByText("SZVTK")).toBeInTheDocument();
    expect(within(sidebar).getByText("owner")).toBeInTheDocument();
    expect(listTeams).toHaveBeenCalledTimes(1);
  });

  it("signs out from the sidebar and from the mobile header", async () => {
    const { auth } = await renderAt("/");
    await userEvent.click(
      within(screen.getByRole("complementary")).getByRole("button", { name: "Sign out" }),
    );
    expect(auth.mocks.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("offers a compact sign-out button in the mobile header", async () => {
    const { auth } = await renderAt("/");
    const header = screen.getByRole("banner");
    await userEvent.click(within(header).getByRole("button", { name: "Sign out" }));
    expect(auth.mocks.signOut).toHaveBeenCalledOnce();
  });
});
