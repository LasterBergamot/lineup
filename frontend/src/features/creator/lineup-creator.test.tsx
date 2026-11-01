import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { ToastProvider } from "@/components/ui/toast";
import { LineupCreator } from "@/features/creator/lineup-creator";
import { emptyValues } from "@/features/creator/resolve";
import { SLOW_PDF_NOTICE_MS } from "@/features/lineup/lineup-form";
import type { Player } from "@/features/players/api";
import type { Team } from "@/features/teams/api";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  createSavedLineup: vi.fn(),
  generateLineup: vi.fn(),
  generateSavedLineup: vi.fn(),
  saveFile: vi.fn(),
}));
vi.mock("@/features/creator/api", () => ({ createSavedLineup: mocks.createSavedLineup }));
vi.mock("@/features/lineup/generate", () => ({
  generateLineup: mocks.generateLineup,
  generateSavedLineup: mocks.generateSavedLineup,
}));
vi.mock("@/features/lineup/download", () => ({ saveFile: mocks.saveFile }));
// The viewer needs pdf.js and a canvas; its own tests cover it.
vi.mock("@/features/preview/pdf-viewer", () => ({
  PdfViewer: ({ file }: { file: Blob }) => <div data-testid="viewer">{file.size} bytes</div>,
}));
// The real combobox is covered by its own tests; this one reports "Listed FC" as a directory team.
vi.mock("@/features/creator/opponent/opponent-combobox", () => ({
  OpponentCombobox: ({
    value,
    onChange,
    teamId,
    ...rest
  }: {
    value: string;
    onChange: (value: string, match?: { directoryId: string }) => void;
    teamId: string;
  }) => (
    <input
      {...rest}
      data-team={teamId}
      value={value}
      onChange={(event) =>
        onChange(
          event.target.value,
          event.target.value === "Listed FC" ? { directoryId: "opp-1" } : undefined,
        )
      }
    />
  ),
}));

const TEAM_ID = "00000000-0000-4000-8000-000000000001";
const ANN: Player = {
  id: "p-ann",
  team_id: TEAM_ID,
  name: "Kovács Anna",
  nssz_number: "MVLSZ1",
  created_at: "",
};
const BEN: Player = { ...ANN, id: "p-ben", name: "Nagy Bence", nssz_number: "MVLSZ2" };
const SAVED = { id: "s-1" };
const PDF = { blob: new Blob(["%PDF"]), filename: "sheet.pdf" };

function SignedIn(props: Parameters<typeof LineupCreator>[0]) {
  return useAuth().status === "signed-in" ? <LineupCreator {...props} /> : null;
}

function renderCreator(
  props: { roster?: Player[]; initialValues?: ReturnType<typeof emptyValues> } = {},
) {
  const team = { ...teamsPage("SZVTK").items[0]!, id: TEAM_ID } as Team;
  const queryClient = testQueryClient();
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <ToastProvider>
          <MemoryRouter>
            <SignedIn
              team={team}
              roster={props.roster ?? [ANN, BEN]}
              initialValues={props.initialValues}
            />
          </MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { invalidate };
}

type User = ReturnType<typeof userEvent.setup>;

/** Fills the match fields that have no default. */
async function fillMatch(user: User, opponent = "Csongrád") {
  await screen.findByLabelText("Opponent");
  await user.type(screen.getByLabelText("Opponent"), opponent);
  await user.type(screen.getByLabelText("Division"), "OB I.");
  await user.type(screen.getByLabelText("Date"), "2026. 11. 1.");
  await user.type(screen.getByLabelText("Coach"), "Kovács Béla");
}

const slot = (n: number) => screen.getByRole("group", { name: `Player ${n}` });
const pick = (n: number, name: string) =>
  userEvent.selectOptions(within(slot(n)).getByLabelText("Player from the roster"), name);

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.createSavedLineup.mockResolvedValue(SAVED);
  mocks.generateLineup.mockResolvedValue(PDF);
  mocks.generateSavedLineup.mockResolvedValue(PDF);
});
afterEach(() => vi.useRealTimers());

describe("LineupCreator form", () => {
  it("starts with one typed-in slot and says when the roster is empty", async () => {
    renderCreator({ roster: [] });
    expect(await screen.findByText(/The roster is empty/)).toBeInTheDocument();
    expect(within(slot(1)).getByLabelText("Cap no.")).toHaveValue(1);
    expect(screen.getByRole("radio", { name: "White" })).toBeChecked();
    expect(screen.getByRole("button", { name: "Remove player 1" })).toBeDisabled();
  });

  it("shows the errors and sends nothing when the form is empty", async () => {
    const user = userEvent.setup();
    renderCreator();
    await user.click(await screen.findByRole("button", { name: "Save lineup" }));
    expect(await screen.findByText("Opponent is required")).toBeInTheDocument();
    expect(screen.getByText("Name is required")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Preview" }));
    expect(await screen.findAllByText("Opponent is required")).not.toHaveLength(0);
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();
    expect(mocks.generateLineup).not.toHaveBeenCalled();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("fills a slot from the roster, locks it, and leaves the player out of the other slots", async () => {
    const user = userEvent.setup();
    renderCreator();
    await screen.findByLabelText("Opponent");
    await pick(1, "Kovács Anna");
    expect(within(slot(1)).getByLabelText("Name")).toHaveValue("Kovács Anna");
    expect(within(slot(1)).getByLabelText("NSSZ number")).toHaveValue("MVLSZ1");
    expect(within(slot(1)).getByLabelText("Name")).toHaveAttribute("readonly");

    await user.click(screen.getByRole("button", { name: /Add player/ }));
    expect(within(slot(2)).getByRole("option", { name: "Kovács Anna" })).toBeDisabled();
    expect(within(slot(2)).getByRole("option", { name: "Nagy Bence" })).toBeEnabled();
    expect(within(slot(1)).getByRole("option", { name: "Kovács Anna" })).toBeEnabled();

    await pick(1, "Type in by hand");
    expect(within(slot(1)).getByLabelText("Name")).toHaveValue("");
    expect(within(slot(1)).getByLabelText("Name")).not.toHaveAttribute("readonly");
    expect(within(slot(2)).getByRole("option", { name: "Kovács Anna" })).toBeEnabled();
  });

  it("adds players with the next free cap number, up to 15, and removes them", async () => {
    const user = userEvent.setup();
    renderCreator();
    const add = await screen.findByRole("button", { name: /Add player/ });
    await user.click(add);
    await user.click(add);
    await user.click(screen.getByRole("button", { name: "Remove player 2" }));
    await user.click(add);
    expect(screen.getAllByLabelText("Cap no.").map((el) => (el as HTMLInputElement).value)).toEqual(
      ["1", "3", "2"],
    );
    for (let i = 0; i < 12; i++) await user.click(add);
    expect(screen.getAllByRole("group", { name: /^Player/ })).toHaveLength(15);
    expect(add).toBeDisabled();
  });

  it("starts from the given values, as when cloning a saved lineup", async () => {
    renderCreator({
      initialValues: {
        ...emptyValues(),
        division: "OB II.",
        coach: "Klón Edző",
        players: [{ cap_number: 4, playerId: "p-ben", name: "Nagy Bence", nssz_number: "MVLSZ2" }],
      },
    });
    expect(await screen.findByLabelText("Division")).toHaveValue("OB II.");
    expect(screen.getByLabelText("Coach")).toHaveValue("Klón Edző");
    expect(within(slot(1)).getByLabelText("Cap no.")).toHaveValue(4);
    expect(within(slot(1)).getByLabelText("Player from the roster")).toHaveValue("p-ben");
    expect(screen.getByLabelText("Opponent")).toHaveValue("");
  });

  it("keeps the entered values in memory only", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillMatch(user);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});

describe("LineupCreator save", () => {
  it("saves roster players and a listed opponent by id, then offers the downloads", async () => {
    const user = userEvent.setup();
    const { invalidate } = renderCreator();
    await fillMatch(user, "Listed FC");
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: /Add player/ }));
    await user.type(within(slot(2)).getByLabelText("Name"), "Kiss Ádám");
    await user.type(within(slot(2)).getByLabelText("NSSZ number"), "MVLSZ9");
    await user.type(screen.getByLabelText("Doctor (optional)"), "Dr. Kis");
    await user.click(screen.getByRole("radio", { name: "Blue" }));
    expect(screen.getByRole("radio", { name: "Blue" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "White" })).not.toBeChecked();

    await user.click(screen.getByRole("button", { name: "Save lineup" }));

    expect(await screen.findByText(/Saved\. You can download it now\./)).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Notifications" })).getByText("Lineup saved"),
    ).toBeInTheDocument();
    expect(mocks.createSavedLineup).toHaveBeenCalledOnce();
    expect(mocks.createSavedLineup.mock.calls[0]![0]).toMatchObject({
      team_id: TEAM_ID,
      source_team_id: TEAM_ID,
      source_opponent_id: "opp-1",
      division: "OB I.",
      cap: "Kék",
      coach: "Kovács Béla",
      doctor: "Dr. Kis",
      players: [
        { source_player_id: "p-ann", cap_number: 1 },
        { name: "Kiss Ádám", nssz_number: "MVLSZ9", cap_number: 2 },
      ],
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["saved"] });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: expect.arrayContaining(["recent-opponents"]),
    });
    expect(screen.getByRole("link", { name: "See saved lineups" })).toHaveAttribute(
      "href",
      "/saved",
    );
    expect(screen.getByRole("button", { name: "Save lineup" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await waitFor(() => expect(mocks.saveFile).toHaveBeenCalledWith(PDF));
    expect(mocks.generateSavedLineup).toHaveBeenCalledWith("s-1", "pdf");
    await user.click(screen.getByRole("button", { name: "Download DOCX" }));
    await waitFor(() => expect(mocks.generateSavedLineup).toHaveBeenCalledWith("s-1", "docx"));
  });

  it("sends a typed-in opponent by name and allows saving again after an edit", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await screen.findByText(/Saved\./);
    expect(mocks.createSavedLineup.mock.calls[0]![0]).toMatchObject({ opponent_name: "Csongrád" });
    expect(mocks.createSavedLineup.mock.calls[0]![0]).not.toHaveProperty("source_opponent_id");

    await user.type(screen.getByLabelText("Match name (optional)"), "Final");
    expect(screen.queryByText(/Saved\./)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await waitFor(() => expect(mocks.createSavedLineup).toHaveBeenCalledTimes(2));
  });

  it("shows only the clicked download as busy while it runs", async () => {
    const user = userEvent.setup();
    mocks.generateSavedLineup.mockReturnValue(new Promise(() => {}));
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await user.click(await screen.findByRole("button", { name: "Download PDF" }));

    expect(screen.getByRole("button", { name: "Download PDF" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(screen.getByRole("button", { name: "Download DOCX" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Download DOCX" })).not.toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("shows a readable message when the download fails", async () => {
    const user = userEvent.setup();
    mocks.generateSavedLineup.mockRejectedValue(new ApiError(504));
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await user.click(await screen.findByRole("button", { name: "Download PDF" }));
    expect(await screen.findByText(/too long/i)).toBeInTheDocument();
  });

  it("maps a 422 onto the fields it names", async () => {
    const user = userEvent.setup();
    mocks.createSavedLineup.mockRejectedValue(
      new ApiError(422, {
        detail: [
          { loc: ["body", "opponent_name"], msg: "String should have at most 120 characters" },
          { loc: ["body", "players", 0, "source_player_id"], msg: "Value error, twice" },
          { loc: ["body", "players"], msg: "Value error, Cap numbers must be unique" },
          { loc: ["body", "cap"], msg: "Input should be 'Fehér' or 'Kék'" },
        ],
      }),
    );
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));

    expect(
      await screen.findByText("String should have at most 120 characters"),
    ).toBeInTheDocument();
    expect(within(slot(1)).getByText("twice")).toBeInTheDocument();
    expect(screen.getByText("Cap numbers must be unique")).toBeInTheDocument();
    expect(screen.getByText("Input should be 'Fehér' or 'Kék'")).toBeInTheDocument();
    expect(screen.getByText(/server rejected some of the details/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Opponent")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows a readable message for any other failure", async () => {
    const user = userEvent.setup();
    mocks.createSavedLineup.mockRejectedValue(new ApiError(404));
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/no longer exists/i);
  });
});

describe("LineupCreator preview", () => {
  it("previews the sheet through the stateless endpoint and closes the panel", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByTestId("viewer")).toHaveTextContent("4 bytes");
    expect(screen.getByRole("complementary", { name: "Preview" })).toBeInTheDocument();
    const [body, format] = mocks.generateLineup.mock.calls[0]!;
    expect(format).toBe("pdf");
    expect(body).toMatchObject({
      match: "SZVTK - Csongrád",
      team_name: "SZVTK",
      players: [{ cap_number: 1, name: "Kovács Anna", nssz_number: "MVLSZ1" }],
    });
    expect(body.doctor).toBeUndefined();
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Close the preview" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(screen.queryByTestId("viewer")).not.toBeInTheDocument();
  });

  it("shows a skeleton, and explains a slow PDF after 5 seconds", async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocks.generateLineup.mockReturnValue(new Promise(() => {}));
    renderCreator();
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    const panel = await screen.findByRole("complementary", { name: "Preview" });
    expect(within(panel).getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview" })).toBeDisabled();
    expect(screen.queryByText(/first one after a break/)).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(SLOW_PDF_NOTICE_MS));
    expect(within(panel).getByText(/first one after a break/)).toBeInTheDocument();
  });

  it("maps a 422 from the preview onto the fields and says so in the panel", async () => {
    const user = userEvent.setup();
    mocks.generateLineup.mockRejectedValue(
      new ApiError(422, { detail: [{ loc: ["body", "match"], msg: "too long" }] }),
    );
    renderCreator();
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    const panel = await screen.findByRole("complementary", { name: "Preview" });
    expect(
      await within(panel).findByText(/server rejected some of the details/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Match name (optional)")).toHaveAttribute("aria-invalid", "true");
  });

  it("shows a readable message in the panel for any other failure", async () => {
    const user = userEvent.setup();
    mocks.generateLineup.mockRejectedValue(new ApiError(503));
    renderCreator();
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Preview" }));
    const panel = await screen.findByRole("complementary", { name: "Preview" });
    expect(await within(panel).findByRole("alert")).toHaveTextContent(/busy or starting up/i);
  });
});
