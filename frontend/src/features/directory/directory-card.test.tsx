import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { AuthProvider } from "@/auth/provider";
import { DirectoryCard } from "@/features/directory/directory-card";
import type { PoolTeam } from "@/features/directory/api";
import { i18n } from "@/i18n";
import { fakeAuthClient, fakeSession, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ searchPool: vi.fn() }));
vi.mock("@/features/directory/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/directory/api")>()),
  searchPool: mocks.searchPool,
}));

const team = (n: number, name: string): PoolTeam => ({
  id: `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`,
  name,
});
const ALL = [team(1, "BVSC"), team(2, "FTC"), team(3, "Szeged")];

function renderCard() {
  const queryClient = testQueryClient();
  const auth = fakeAuthClient(fakeSession());
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={auth.client}>
        <DirectoryCard />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { queryClient };
}

const names = () =>
  within(screen.getByRole("list", { name: "Listed teams" }))
    .getAllByRole("listitem")
    .map((item) => item.textContent);

beforeEach(() => {
  mocks.searchPool.mockReset();
  mocks.searchPool.mockResolvedValue(ALL);
});

describe("DirectoryCard", () => {
  it("lists the first teams alphabetically with a blank search, names only", async () => {
    renderCard();
    expect(screen.getByRole("heading", { name: "Opponent directory" })).toBeInTheDocument();
    expect(screen.getByText(/chose to be listed/)).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(await screen.findByText("Szeged")).toBeInTheDocument();
    expect(names()).toEqual(["BVSC", "FTC", "Szeged"]);
    expect(mocks.searchPool).toHaveBeenCalledTimes(1);
    expect(mocks.searchPool).toHaveBeenCalledWith("", 20);
    for (const { id } of ALL) expect(document.body.textContent).not.toContain(id);
  });

  it("offers a bounded search box", async () => {
    renderCard();
    const box = screen.getByRole("searchbox", { name: "Search teams" });
    expect(box).toHaveAttribute("maxLength", "120");
    await screen.findByText("BVSC");
  });

  it("sends one trimmed request once typing pauses", async () => {
    renderCard();
    await screen.findByText("BVSC");
    mocks.searchPool.mockResolvedValue([ALL[2]]);
    await userEvent.type(screen.getByRole("searchbox"), "  Sze ");
    await waitFor(() => expect(mocks.searchPool).toHaveBeenCalledTimes(2));
    expect(mocks.searchPool).toHaveBeenLastCalledWith("Sze", 20);
    await waitFor(() => expect(names()).toEqual(["Szeged"]));
    // Nothing else went out after the pause.
    await act(() => new Promise((resolve) => setTimeout(resolve, 400)));
    expect(mocks.searchPool).toHaveBeenCalledTimes(2);
  });

  it("keeps the previous results on screen while a new search runs", async () => {
    renderCard();
    await screen.findByText("BVSC");
    let answer: (teams: PoolTeam[]) => void = () => {};
    mocks.searchPool.mockReturnValue(new Promise<PoolTeam[]>((resolve) => (answer = resolve)));
    await userEvent.type(screen.getByRole("searchbox"), "FT");
    await waitFor(() => expect(mocks.searchPool).toHaveBeenLastCalledWith("FT", 20));
    expect(names()).toEqual(["BVSC", "FTC", "Szeged"]);
    expect(screen.getByRole("list", { name: "Listed teams" })).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    act(() => answer([ALL[1]!]));
    await waitFor(() => expect(names()).toEqual(["FTC"]));
    expect(screen.getByRole("list", { name: "Listed teams" })).toHaveAttribute(
      "aria-busy",
      "false",
    );
  });

  it("says when a search finds nothing", async () => {
    renderCard();
    await screen.findByText("BVSC");
    mocks.searchPool.mockResolvedValue([]);
    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    expect(await screen.findByText("No teams found.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("says when nobody is listed yet", async () => {
    mocks.searchPool.mockResolvedValue([]);
    renderCard();
    expect(await screen.findByText("No teams are listed yet.")).toBeInTheDocument();
  });

  it("notes that only the first page is shown when it is full", async () => {
    mocks.searchPool.mockResolvedValue(
      Array.from({ length: 20 }, (_, i) => team(i + 1, `Team ${i + 1}`)),
    );
    renderCard();
    expect(await screen.findByText(/Showing the first 20 teams/)).toBeInTheDocument();
  });

  it("does not note a partial page", async () => {
    renderCard();
    await screen.findByText("BVSC");
    expect(screen.queryByText(/Showing the first/)).not.toBeInTheDocument();
  });

  it("explains a failure and retries", async () => {
    mocks.searchPool.mockRejectedValueOnce(new ApiError(503));
    renderCard();
    expect(await screen.findByRole("alert")).toHaveTextContent(/busy or starting up/);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("FTC")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("caches searches per user and waits for the user to be known", async () => {
    const { queryClient } = renderCard();
    await screen.findByText("BVSC");
    expect(queryClient.getQueryData(["pool", fakeSession().user.id, ""])).toEqual(ALL);
    // The query keyed by no one (while auth was loading) never ran.
    expect(queryClient.getQueryState(["pool", null, ""])?.fetchStatus ?? "idle").toBe("idle");
    expect(queryClient.getQueryData(["pool", null, ""])).toBeUndefined();
    expect(mocks.searchPool).toHaveBeenCalledTimes(1);
  });

  it("speaks Hungarian", async () => {
    renderCard();
    await screen.findByText("BVSC");
    await act(() => i18n.changeLanguage("hu"));
    try {
      expect(screen.getByRole("heading", { name: "Ellenfél-névjegyzék" })).toBeInTheDocument();
      expect(screen.getByRole("searchbox", { name: "Keresés a csapatok között" })).toBeVisible();
    } finally {
      await act(() => i18n.changeLanguage("en"));
    }
  });
});
