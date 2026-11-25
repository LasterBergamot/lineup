import { QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { NO_FILTERS, type SavedLineup } from "@/features/saved/api";
import { SavedLineups } from "@/features/saved/saved-lineups";
import type { Team } from "@/features/teams/api";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listSavedLineups: vi.fn(),
  deleteSavedLineup: vi.fn(),
  generateSavedLineup: vi.fn(),
  saveFile: vi.fn(),
  useAfterDelay: vi.fn(),
}));
vi.mock("@/features/saved/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/saved/api")>()),
  listSavedLineups: mocks.listSavedLineups,
  deleteSavedLineup: mocks.deleteSavedLineup,
}));
vi.mock("@/features/lineup/generate", () => ({ generateSavedLineup: mocks.generateSavedLineup }));
vi.mock("@/features/lineup/download", () => ({ saveFile: mocks.saveFile }));
vi.mock("@/lib/use-after-delay", () => ({ useAfterDelay: mocks.useAfterDelay }));
// pdf.js does not run in jsdom; the viewer has its own tests.
vi.mock("@/features/preview/pdf-viewer", () => ({
  PdfViewer: ({ file }: { file: Blob & { label?: string } }) => <p>{`pdf: ${file.label}`}</p>,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";

function lineup(n: number, overrides: Partial<SavedLineup> = {}): SavedLineup {
  return {
    id: `l-${n}`,
    team_id: TEAM,
    team_name: "SZVTK",
    opponent_name: `Opponent ${n}`,
    match_name: `SZVTK - Opponent ${n}`,
    division: "OB II.",
    cap: "Kék",
    date: `2026. 10. ${n}.`,
    match_date: null,
    match_time: null,
    location: null,
    is_home: null,
    coach: "Coach",
    doctor: null,
    assistant_coach: null,
    team_leader: null,
    ball_thrower: null,
    source_team_id: TEAM,
    source_opponent_id: null,
    players: [],
    created_at: "2026-10-05T10:00:00",
    updated_at: "2026-10-05T10:00:00",
    ...overrides,
  };
}

/** One page as `listSavedLineups` returns it; `total` defaults to "this is everything". */
const pageOf = (items: SavedLineup[], total = items.length, offset = 0) => ({
  items,
  total,
  offset,
});

/** A file whose `label` the mocked viewer prints, so a test can tell previews apart. */
const pdfFile = (label: string) => ({ blob: Object.assign(new Blob(["%PDF"]), { label }) });

/** Shows where "Edit" or "Clone" navigated to, and the whole router state it handed the creator. */
function LineupProbe() {
  return <p>{`creator with ${JSON.stringify(useLocation().state)}`}</p>;
}

function SignedIn({ team }: { team: Team }) {
  return useAuth().status === "signed-in" ? <SavedLineups team={team} /> : null;
}

function renderList() {
  const team = teamsPage("SZVTK").items[0] as Team;
  const queryClient = testQueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <MemoryRouter initialEntries={["/saved"]}>
          <Routes>
            <Route path="/saved" element={<SignedIn team={team} />} />
            <Route path="/" element={<LineupProbe />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { queryClient };
}

const row = (match: string) =>
  screen.getByRole("listitem", { name: (_, el) => el.textContent?.includes(match) ?? false });
const rowOf = async (match: string) => {
  await screen.findByText(match);
  return screen.getByText(match).closest("li")!;
};

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listSavedLineups.mockResolvedValue(pageOf([lineup(2), lineup(1, { cap: "Fehér" })]));
  mocks.useAfterDelay.mockReturnValue(false);
});

describe("SavedLineups", () => {
  it("lists the team's lineups with their match details", async () => {
    renderList();
    const list = await screen.findByRole("list", { name: "Saved lineups of SZVTK" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("SZVTK - Opponent 2");
    expect(items[0]).toHaveTextContent("2026. 10. 2. · OB II. · Blue caps · Opponent: Opponent 2");
    expect(items[1]).toHaveTextContent("White caps");
    expect(mocks.listSavedLineups).toHaveBeenCalledWith(TEAM, NO_FILTERS, 0);
  });

  it("shows the location after the details when the lineup has one", async () => {
    mocks.listSavedLineups.mockResolvedValue(
      pageOf([lineup(2, { location: "Szeged" }), lineup(1)]),
    );
    renderList();
    const items = within(await screen.findByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Opponent: Opponent 2 · Location: Szeged");
    expect(items[1]).not.toHaveTextContent("Location");
  });

  it("shows the home/away side, and a dash for an old lineup that never said", async () => {
    mocks.listSavedLineups.mockResolvedValue(
      pageOf([lineup(3, { is_home: true }), lineup(2, { is_home: false }), lineup(1)]),
    );
    renderList();
    const items = within(await screen.findByRole("list")).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Home/away: Home");
    expect(items[1]).toHaveTextContent("Home/away: Away");
    expect(items[2]).toHaveTextContent("Home/away: –");
  });

  it("explains where lineups come from when there are none", async () => {
    mocks.listSavedLineups.mockResolvedValue(pageOf([]));
    renderList();
    expect(await screen.findByText(/No saved lineups yet/)).toBeInTheDocument();
  });

  it("shows a lineup's PDF in the preview panel and closes it again", async () => {
    mocks.generateSavedLineup.mockResolvedValue(pdfFile("two"));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    const panel = screen.getByRole("complementary", { name: "Preview: SZVTK - Opponent 2" });
    expect(await within(panel).findByText("pdf: two")).toBeInTheDocument();
    expect(mocks.generateSavedLineup).toHaveBeenCalledWith("l-2", "pdf");
    expect(within(panel).getByRole("button", { name: "Enlarge" })).toBeInTheDocument();
    const row = await rowOf("SZVTK - Opponent 2");
    expect(row).toHaveAttribute("aria-current", "true");
    // The row's Preview button, plus the "Preview" badge on the selected row only.
    expect(within(row).getAllByText("Preview")).toHaveLength(2);
    expect(within(await rowOf("SZVTK - Opponent 1")).getAllByText("Preview")).toHaveLength(1);
    expect(await rowOf("SZVTK - Opponent 1")).not.toHaveAttribute("aria-current");
    await userEvent.click(within(panel).getByRole("button", { name: "Close the preview" }));
    expect(row).not.toHaveAttribute("aria-current");
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("shows a placeholder while the preview loads", async () => {
    mocks.generateSavedLineup.mockReturnValue(new Promise(() => {}));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 1" }),
    );
    const panel = screen.getByRole("complementary");
    expect(within(panel).getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("keeps each preview in memory, so reopening one does not generate it again", async () => {
    mocks.generateSavedLineup.mockImplementation(async (id: string) => pdfFile(id));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    expect(await screen.findByText("pdf: l-2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Preview SZVTK - Opponent 1" }));
    expect(await screen.findByText("pdf: l-1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Preview SZVTK - Opponent 2" }));
    expect(await screen.findByText("pdf: l-2")).toBeInTheDocument();
    expect(mocks.generateSavedLineup).toHaveBeenCalledTimes(2);
  });

  it("generates the preview again for a new version of an edited lineup", async () => {
    mocks.generateSavedLineup.mockImplementation(async (id: string) => pdfFile(id));
    const { queryClient } = renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    expect(await screen.findByText("pdf: l-2")).toBeInTheDocument();
    // Another member edits it; the list comes back with a newer version.
    mocks.generateSavedLineup.mockImplementation(async (id: string) => pdfFile(`${id} v2`));
    mocks.listSavedLineups.mockResolvedValue(
      pageOf([lineup(2, { updated_at: "2026-11-24T09:00:00" }), lineup(1)]),
    );
    await act(() =>
      queryClient.refetchQueries({ predicate: (q) => !q.queryKey.includes("preview") }),
    );
    await screen.findByText(/^Edited /);
    await userEvent.click(screen.getByRole("button", { name: "Preview SZVTK - Opponent 2" }));
    expect(await screen.findByText("pdf: l-2 v2")).toBeInTheDocument();
    expect(mocks.generateSavedLineup).toHaveBeenCalledTimes(2);
  });

  it("says when a lineup was edited, and nothing for one never edited", async () => {
    mocks.listSavedLineups.mockResolvedValue(
      pageOf([lineup(2, { updated_at: "2026-11-24T09:30:00Z" }), lineup(1)]),
    );
    renderList();
    expect(await rowOf("SZVTK - Opponent 2")).toHaveTextContent(/Edited Nov 24, 2026/);
    expect(await rowOf("SZVTK - Opponent 1")).not.toHaveTextContent(/Edited/);
  });

  it("never starts a preview from hovering, however long the pointer rests on a row", async () => {
    mocks.generateSavedLineup.mockImplementation(async (id: string) => pdfFile(id));
    renderList();
    const first = await rowOf("SZVTK - Opponent 2");
    vi.useFakeTimers();
    try {
      fireEvent.mouseEnter(first);
      act(() => vi.advanceTimersByTime(60_000));
      fireEvent.mouseLeave(first);
      fireEvent.mouseEnter(row("SZVTK - Opponent 1"));
      act(() => vi.advanceTimersByTime(60_000));
    } finally {
      vi.useRealTimers();
    }
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(mocks.generateSavedLineup).not.toHaveBeenCalled();
  });

  it("says a previewed lineup is gone when the server answers 404", async () => {
    mocks.generateSavedLineup.mockRejectedValue(new ApiError(404));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    expect(await within(screen.getByRole("complementary")).findByRole("alert")).toHaveTextContent(
      "This lineup no longer exists",
    );
  });

  it("explains other preview failures without showing server text", async () => {
    mocks.generateSavedLineup.mockRejectedValue(new ApiError(504, { detail: "secret" }));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    const alert = await within(screen.getByRole("complementary")).findByRole("alert");
    expect(alert).not.toHaveTextContent("This lineup no longer exists");
    expect(alert).not.toHaveTextContent("secret");
  });

  it("tells the user when a PDF takes a while", async () => {
    mocks.useAfterDelay.mockReturnValue(true);
    renderList();
    expect(await screen.findByText(/Generating the PDF/)).toBeInTheDocument();
  });

  it.each([
    ["PDF", "pdf"],
    ["DOCX", "docx"],
  ] as const)("downloads a lineup as %s", async (label, format) => {
    const file = { blob: new Blob(["x"]), filename: `sheet.${format}` };
    mocks.generateSavedLineup.mockResolvedValue(file);
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: `Download SZVTK - Opponent 1 as ${label}` }),
    );
    await waitFor(() => expect(mocks.saveFile).toHaveBeenCalledWith(file));
    expect(mocks.generateSavedLineup).toHaveBeenCalledWith("l-1", format);
  });

  it("disables the downloads while one is running", async () => {
    mocks.generateSavedLineup.mockReturnValue(new Promise(() => {}));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Download SZVTK - Opponent 1 as PDF" }),
    );
    expect(
      screen.getByRole("button", { name: "Download SZVTK - Opponent 2 as DOCX" }),
    ).toBeDisabled();
  });

  it("reloads the list when a download finds the lineup gone", async () => {
    mocks.generateSavedLineup.mockRejectedValue(new ApiError(404));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Download SZVTK - Opponent 1 as PDF" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("This lineup no longer exists");
    await waitFor(() => expect(mocks.listSavedLineups).toHaveBeenCalledTimes(2));
  });

  it("reports other download failures without reloading", async () => {
    mocks.generateSavedLineup.mockRejectedValue(new ApiError(0));
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Download SZVTK - Opponent 1 as DOCX" }),
    );
    expect(await screen.findByRole("alert")).not.toHaveTextContent("no longer exists");
    expect(mocks.listSavedLineups).toHaveBeenCalledOnce();
  });

  it("opens the creator with only the id of the lineup to clone, no names", async () => {
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Clone to new match: SZVTK - Opponent 2" }),
    );
    expect(screen.getByText('creator with {"cloneFromId":"l-2"}')).toBeInTheDocument();
  });

  it("opens the creator with only the id of the lineup to edit, no names", async () => {
    await userEvent.click(
      await (renderList(), screen.findByRole("button", { name: "Edit SZVTK - Opponent 2" })),
    );
    expect(screen.getByText('creator with {"editFromId":"l-2"}')).toBeInTheDocument();
  });

  it("deletes a lineup after a confirm and reloads the list", async () => {
    mocks.deleteSavedLineup.mockResolvedValue(undefined);
    renderList();
    await userEvent.click(await screen.findByRole("button", { name: "Delete SZVTK - Opponent 1" }));
    mocks.listSavedLineups.mockResolvedValue(pageOf([lineup(2)]));
    await userEvent.click(screen.getByRole("button", { name: "Delete lineup" }));
    expect(mocks.deleteSavedLineup).toHaveBeenCalledWith("l-1");
    await waitFor(() => expect(screen.queryByText("SZVTK - Opponent 1")).not.toBeInTheDocument());
  });

  it("closes the preview of a lineup that was deleted, and keeps any other one open", async () => {
    mocks.generateSavedLineup.mockImplementation(async (id: string) => pdfFile(id));
    mocks.deleteSavedLineup.mockResolvedValue(undefined);
    renderList();
    await userEvent.click(
      await screen.findByRole("button", { name: "Preview SZVTK - Opponent 2" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Delete SZVTK - Opponent 1" }));
    mocks.listSavedLineups.mockResolvedValue(pageOf([lineup(2)]));
    await userEvent.click(screen.getByRole("button", { name: "Delete lineup" }));
    await waitFor(() => expect(screen.queryByText("SZVTK - Opponent 1")).not.toBeInTheDocument());
    expect(screen.getByRole("complementary")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Delete SZVTK - Opponent 2" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete lineup" }));
    await waitFor(() => expect(screen.queryByRole("complementary")).not.toBeInTheDocument());
  });

  it("shows the running delete on its own row only", async () => {
    mocks.deleteSavedLineup.mockReturnValue(new Promise(() => {}));
    renderList();
    await userEvent.click(await screen.findByRole("button", { name: "Delete SZVTK - Opponent 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete lineup" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Delete lineup" })).toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "Delete SZVTK - Opponent 2" })).toBeEnabled();
  });

  it("says so when a delete fails", async () => {
    mocks.deleteSavedLineup.mockRejectedValue(new ApiError(404));
    renderList();
    await userEvent.click(await screen.findByRole("button", { name: "Delete SZVTK - Opponent 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Delete lineup" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This lineup no longer exists");
  });

  it("offers a retry when the list cannot be loaded", async () => {
    mocks.listSavedLineups.mockRejectedValue(new ApiError(0));
    renderList();
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("SavedLineups filters", () => {
  const lastCall = () => mocks.listSavedLineups.mock.calls.at(-1)!;

  it("narrows the list as the user types, after a short pause, and keeps the other filters", async () => {
    renderList();
    await screen.findByRole("list", { name: "Saved lineups of SZVTK" });
    await userEvent.type(screen.getByRole("searchbox", { name: "Opponent" }), "ftc");
    // Nothing is sent per keystroke: the term goes out once typing stops.
    expect(mocks.listSavedLineups).toHaveBeenCalledOnce();
    await waitFor(() => expect(lastCall()[1]).toEqual({ ...NO_FILTERS, opponent: "ftc" }));

    await userEvent.type(screen.getByRole("searchbox", { name: "Location" }), "Szeged");
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-10-31" } });
    await waitFor(() =>
      expect(lastCall()).toEqual([
        TEAM,
        { opponent: "ftc", location: "Szeged", dateFrom: "2026-10-01", dateTo: "2026-10-31" },
        0,
      ]),
    );
  });

  it("keeps the date pickers consistent with each other", async () => {
    renderList();
    await screen.findByRole("list", { name: "Saved lineups of SZVTK" });
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-10-31" } });
    expect(screen.getByLabelText("From date")).toHaveAttribute("max", "2026-10-31");
    expect(screen.getByLabelText("To date")).toHaveAttribute("min", "2026-10-01");
  });

  it("says so when nothing matches, and Clear filters brings the list back", async () => {
    mocks.listSavedLineups.mockImplementation(async (_team: string, filters) =>
      filters.opponent ? pageOf([]) : pageOf([lineup(2)]),
    );
    renderList();
    await screen.findByText("SZVTK - Opponent 2");
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();

    await userEvent.type(screen.getByRole("searchbox", { name: "Opponent" }), "zzz");
    expect(await screen.findByText("No saved lineups match these filters.")).toBeInTheDocument();
    expect(screen.queryByText(/No saved lineups yet/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getByRole("searchbox", { name: "Opponent" })).toHaveValue("");
    expect(await screen.findByText("SZVTK - Opponent 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear filters" })).not.toBeInTheDocument();
  });

  it("keeps the previous rows while a new search runs", async () => {
    mocks.listSavedLineups.mockImplementation(async (_team: string, filters) =>
      filters.opponent ? new Promise(() => {}) : pageOf([lineup(2)]),
    );
    renderList();
    await screen.findByText("SZVTK - Opponent 2");
    await userEvent.type(screen.getByRole("searchbox", { name: "Opponent" }), "f");
    await waitFor(() => expect(mocks.listSavedLineups).toHaveBeenCalledTimes(2));
    expect(screen.getByText("SZVTK - Opponent 2")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Saved lineups of SZVTK" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("reads the next page on Show more and stops when everything is shown", async () => {
    mocks.listSavedLineups.mockImplementation(async (_team: string, _f, offset: number) =>
      offset === 0 ? pageOf([lineup(2)], 2) : pageOf([lineup(1)], 2, offset),
    );
    renderList();
    await screen.findByText("SZVTK - Opponent 2");
    expect(screen.getByText("Showing 1 of 2 lineups")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("SZVTK - Opponent 1")).toBeInTheDocument();
    expect(mocks.listSavedLineups).toHaveBeenLastCalledWith(TEAM, NO_FILTERS, 1);
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });

  it("stops paging at an empty page when lineups were deleted meanwhile", async () => {
    mocks.listSavedLineups.mockImplementation(async (_team: string, _f, offset: number) =>
      offset === 0 ? pageOf([lineup(2)], 5) : pageOf([], 5, offset),
    );
    renderList();
    await screen.findByText("SZVTK - Opponent 2");
    await userEvent.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument(),
    );
  });

  it("never puts the search terms in the address bar or in storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    renderList();
    await screen.findByRole("list", { name: "Saved lineups of SZVTK" });
    setItem.mockClear();
    await userEvent.type(screen.getByRole("searchbox", { name: "Opponent" }), "secret");
    await waitFor(() => expect(lastCall()[1].opponent).toBe("secret"));
    expect(window.location.search).toBe("");
    expect(setItem.mock.calls.flat().join(" ")).not.toContain("secret");
    setItem.mockRestore();
  });
});
