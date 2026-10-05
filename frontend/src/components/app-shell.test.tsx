import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { AppRoutes } from "@/app";
import { BackendStatusProvider } from "@/backend-status/provider";

function renderAt(path: string) {
  return render(
    <BackendStatusProvider probe={async () => "ok"}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </BackendStatusProvider>,
  );
}

describe("AppShell", () => {
  it("shows the same three destinations in the sidebar and the bottom bar", () => {
    renderAt("/");
    for (const name of ["Sidebar", "Bottom"]) {
      const nav = screen.getByRole("navigation", { name });
      expect(
        within(nav)
          .getAllByRole("link")
          .map((a) => a.textContent),
      ).toEqual(["Lineup", "Roster", "Saved"]);
    }
  });

  it("renders the routed page inside the shell and marks the active link", () => {
    renderAt("/roster");
    expect(screen.getByRole("heading", { name: "Roster" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Sidebar" });
    expect(within(nav).getByRole("link", { name: "Roster" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(nav).getByRole("link", { name: "Lineup" })).not.toHaveAttribute("aria-current");
  });

  it("navigates between pages", async () => {
    renderAt("/");
    await userEvent.click(
      within(screen.getByRole("navigation", { name: "Bottom" })).getByRole("link", {
        name: "Saved",
      }),
    );
    expect(screen.getByRole("heading", { name: "Saved lineups" })).toBeInTheDocument();
  });

  it("shows a not-found page for unknown addresses", () => {
    renderAt("/nope");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("toggles the dark theme and remembers it", async () => {
    renderAt("/");
    const [toggle] = screen.getAllByRole("button", { name: "Switch to dark theme" });
    await userEvent.click(toggle!);
    expect(document.documentElement).toHaveClass("dark");
    expect(localStorage.getItem("lineup-theme")).toBe("dark");
    await userEvent.click(screen.getAllByRole("button", { name: "Switch to light theme" })[0]!);
    expect(document.documentElement).not.toHaveClass("dark");
    expect(localStorage.getItem("lineup-theme")).toBe("light");
  });
});
