import { QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { ToastProvider } from "@/components/ui/toast";
import { SavedLineupGoneError, type SavedLineup } from "@/features/creator/api";
import { LineupCreator } from "@/features/creator/lineup-creator";
import { emptyValues, valuesForEdit } from "@/features/creator/resolve";
import { SLOW_PDF_NOTICE_MS } from "@/features/lineup/lineup-form";
import type { Player } from "@/features/players/api";
import type { Staff } from "@/features/staff/api";
import type { Team } from "@/features/teams/api";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";
import { unsavedProbe } from "@/test/unsaved";

const mocks = vi.hoisted(() => ({
  createSavedLineup: vi.fn(),
  updateSavedLineup: vi.fn(),
  generateLineup: vi.fn(),
  generateSavedLineup: vi.fn(),
  saveFile: vi.fn(),
}));
vi.mock("@/features/creator/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/creator/api")>()),
  createSavedLineup: mocks.createSavedLineup,
  updateSavedLineup: mocks.updateSavedLineup,
}));
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

/** Shows where the creator navigated to. */
function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function SignedIn(props: Parameters<typeof LineupCreator>[0]) {
  return useAuth().status === "signed-in" ? <LineupCreator {...props} /> : null;
}

function renderCreator(
  props: {
    roster?: Player[];
    staff?: Staff[];
    initialValues?: ReturnType<typeof emptyValues>;
    division?: string | null;
    edit?: Parameters<typeof LineupCreator>[0]["edit"];
  } = {},
) {
  const team = {
    ...teamsPage("SZVTK").items[0]!,
    id: TEAM_ID,
    division: props.division ?? null,
  } as Team;
  const queryClient = testQueryClient();
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");
  const unsaved = unsavedProbe();
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <ToastProvider>
          <MemoryRouter>
            <unsaved.Wrapper>
              <SignedIn
                team={team}
                roster={props.roster ?? [ANN, BEN]}
                staff={props.staff}
                initialValues={props.initialValues}
                edit={props.edit}
              />
              <Where />
            </unsaved.Wrapper>
          </MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { invalidate, isDirty: unsaved.isDirty };
}

type User = ReturnType<typeof userEvent.setup>;

/** Fills the match fields that have no default. */
async function fillMatch(user: User, opponent = "Csongrád") {
  await screen.findByLabelText("Opponent");
  await user.type(screen.getByLabelText("Opponent"), opponent);
  await user.type(screen.getByLabelText("Division"), "OB I.");
  await user.type(screen.getByLabelText("Coach"), "Kovács Béla");
}

/** The row of one cap number. */
const slot = (n: number) => screen.getByLabelText(`Cap no. ${n}`);
const picker = (n: number) => within(slot(n)).getByLabelText("Player from the roster");
/** Opens the row's picker and clicks the option (an option's name carries the NSSZ number). */
const pick = async (n: number, name: string) => {
  await userEvent.click(picker(n));
  await userEvent.click(screen.getByRole("option", { name: new RegExp(`^${name}`) }));
};

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.createSavedLineup.mockResolvedValue(SAVED);
  mocks.generateLineup.mockResolvedValue(PDF);
  mocks.generateSavedLineup.mockResolvedValue(PDF);
});
afterEach(() => vi.useRealTimers());

describe("LineupCreator form", () => {
  it("starts a fresh lineup with the team's default division, editable and not dirty", async () => {
    const { isDirty } = renderCreator({ division: "OB II." });
    const division = await screen.findByLabelText("Division");
    expect(division).toHaveValue("OB II.");
    expect(isDirty()).toBe(false);
    await userEvent.clear(division);
    await userEvent.type(division, "Cup");
    expect(division).toHaveValue("Cup");
  });

  it("starts on today's local date with no time, and is not dirty", async () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 24, 23, 59), toFake: ["Date"] });
    const { isDirty } = renderCreator();
    expect(await screen.findByLabelText("Date")).toHaveValue("2026-11-24");
    expect(screen.getByLabelText("Start time (optional)")).toHaveValue("");
    expect(isDirty()).toBe(false);
  });

  it("starts on the next day just after local midnight", async () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 25, 0, 1), toFake: ["Date"] });
    renderCreator();
    expect(await screen.findByLabelText("Date")).toHaveValue("2026-11-25");
  });

  it("requires a date: a cleared one is an error and nothing is sent", async () => {
    const user = userEvent.setup();
    renderCreator();
    await user.clear(await screen.findByLabelText("Date"));
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    expect(await screen.findByText("Date is required")).toBeInTheDocument();
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();
  });

  it("keeps the lineup's own division over the team default when one is given", async () => {
    renderCreator({ division: "OB II.", initialValues: { ...emptyValues(), division: "OB I." } });
    expect(await screen.findByLabelText("Division")).toHaveValue("OB I.");
  });

  it("starts with the 15 empty cap rows in cap order and says when the roster is empty", async () => {
    renderCreator({ roster: [] });
    expect(await screen.findByText(/The roster is empty/)).toBeInTheDocument();
    const rows = screen.getAllByRole("group", { name: /^Cap no\./ });
    expect(rows.map((row) => row.getAttribute("aria-label"))).toEqual(
      Array.from({ length: 15 }, (_, i) => `Cap no. ${i + 1}`),
    );
    expect(within(slot(9)).getByText("9")).toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add player/ })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "White" })).toBeChecked();
    expect(screen.getByRole("button", { name: "Clear row 1" })).toBeDisabled();
    expect(screen.getByText("(0 of 15)")).toBeInTheDocument();
  });

  it("shows the errors and sends nothing when the form is empty", async () => {
    const user = userEvent.setup();
    renderCreator();
    await user.click(await screen.findByRole("button", { name: "Save lineup" }));
    expect(await screen.findByText("Opponent is required")).toBeInTheDocument();
    expect(screen.getByText("Add at least one player")).toBeInTheDocument();
    expect(screen.queryByText("Name is required")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Preview" }));
    expect(await screen.findAllByText("Opponent is required")).not.toHaveLength(0);
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();
    expect(mocks.generateLineup).not.toHaveBeenCalled();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("lists the roster in Hungarian alphabetical order, whatever order the API sent", async () => {
    renderCreator({ roster: [BEN, ANN] });
    await screen.findByLabelText("Opponent");
    await userEvent.click(picker(1));
    const options = within(slot(1))
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options).toEqual(["Type in by hand", "Kovács AnnaMVLSZ1", "Nagy BenceMVLSZ2"]);
  });

  it("fills a row from the roster, locks it, and leaves the player out of the other rows", async () => {
    const user = userEvent.setup();
    renderCreator();
    await screen.findByLabelText("Opponent");
    await pick(1, "Kovács Anna");
    expect(within(slot(1)).getByLabelText("Name")).toHaveValue("Kovács Anna");
    expect(within(slot(1)).getByLabelText("NSSZ number")).toHaveValue("MVLSZ1");
    expect(within(slot(1)).getByLabelText("Name")).toHaveAttribute("readonly");

    await user.click(picker(2));
    const taken = within(slot(2)).getByRole("option", { name: /^Kovács Anna/ });
    expect(taken).toHaveAttribute("aria-disabled", "true");
    expect(within(slot(2)).getByRole("option", { name: /^Nagy Bence/ })).not.toHaveAttribute(
      "aria-disabled",
    );
    // Picking the taken player does nothing.
    await user.click(taken);
    expect(picker(2)).toHaveValue("");
    await user.keyboard("{Escape}");
    await user.click(picker(1));
    expect(within(slot(1)).getByRole("option", { name: /^Kovács Anna/ })).not.toHaveAttribute(
      "aria-disabled",
    );
    await user.keyboard("{Escape}");

    await user.click(screen.getByRole("button", { name: "Clear row 1" }));
    expect(within(slot(1)).getByLabelText("Name")).toHaveValue("");
    expect(within(slot(1)).getByLabelText("Name")).not.toHaveAttribute("readonly");
    await user.click(picker(2));
    expect(within(slot(2)).getByRole("option", { name: /^Kovács Anna/ })).not.toHaveAttribute(
      "aria-disabled",
    );
    await user.keyboard("{Escape}");

    // Switching a row back to "type in by hand" empties it as well.
    await pick(1, "Nagy Bence");
    await pick(1, "Type in by hand");
    expect(within(slot(1)).getByLabelText("NSSZ number")).toHaveValue("");
  });

  it("flags a half-filled row, and Clear empties it and drops its error", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.type(within(slot(3)).getByLabelText("NSSZ number"), "MVLSZ7");
    expect(screen.getByText("(2 of 15)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    expect(await within(slot(3)).findByText("Name is required")).toBeInTheDocument();
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();

    const clear = screen.getByRole("button", { name: "Clear row 3" });
    await user.click(clear);
    expect(within(slot(3)).getByLabelText("NSSZ number")).toHaveValue("");
    expect(within(slot(3)).queryByText("Name is required")).not.toBeInTheDocument();
    expect(clear).toBeDisabled();
    expect(screen.getByText("(1 of 15)")).toBeInTheDocument();
  });

  it("starts from the given values, as when cloning a saved lineup", async () => {
    renderCreator({
      initialValues: {
        ...emptyValues(),
        division: "OB II.",
        coach: "Klón Edző",
        players: emptyValues().players.map((row) =>
          row.cap_number === 4
            ? { ...row, playerId: "p-ben", name: "Nagy Bence", nssz_number: "MVLSZ2" }
            : row,
        ),
      },
    });
    expect(await screen.findByLabelText("Division")).toHaveValue("OB II.");
    expect(screen.getByLabelText("Coach")).toHaveValue("Klón Edző");
    expect(picker(4)).toHaveValue("Nagy Bence");
    expect(picker(1)).toHaveValue("");
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

function staffEntry(name: string, role: Staff["role"], is_default = false): Staff {
  return {
    id: `st-${name}`,
    team_id: TEAM_ID,
    role,
    name,
    source_player_id: null,
    is_default,
    created_at: "",
  };
}

const STAFF = [
  staffEntry("Zala Zoltán", "coach"),
  staffEntry("Edző Ede", "coach", true),
  staffEntry("Ács Ádám", "coach"),
  staffEntry("Vezető Vera", "team_leader", true),
  staffEntry("Dobó Dóra", "ball_thrower"),
];

describe("LineupCreator staff pickers", () => {
  it("starts a new lineup with each role's default, not dirty, and leaves the doctor empty", async () => {
    const { isDirty } = renderCreator({ staff: STAFF });
    expect(await screen.findByRole("combobox", { name: "Coach" })).toHaveValue("Edző Ede");
    expect(screen.getByRole("combobox", { name: "Team leader (optional)" })).toHaveValue(
      "Vezető Vera",
    );
    // A role without a default starts empty; the doctor stays a plain input.
    expect(screen.getByRole("combobox", { name: "Ball thrower (optional)" })).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Assistant coach (optional)" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Doctor (optional)" })).toHaveValue("");
    expect(isDirty()).toBe(false);
  });

  it("offers the role's entries, default first, and saves the picked or typed name", async () => {
    const user = userEvent.setup();
    mocks.createSavedLineup.mockResolvedValue(SAVED);
    const { isDirty } = renderCreator({ staff: STAFF });
    const coach = await screen.findByRole("combobox", { name: "Coach" });
    await user.click(coach);
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Edző Ede",
      "Ács Ádám",
      "Zala Zoltán",
    ]);
    await user.click(screen.getByRole("option", { name: "Ács Ádám" }));
    expect(coach).toHaveValue("Ács Ádám");
    expect(isDirty()).toBe(true);
    // Free text still works, for a name that is not on the staff list.
    const thrower = screen.getByRole("combobox", { name: "Ball thrower (optional)" });
    await user.type(thrower, "Új Dobó");
    await user.type(screen.getByLabelText("Opponent"), "Csongrád");
    await user.type(screen.getByLabelText("Division"), "OB I.");
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await waitFor(() => expect(mocks.createSavedLineup).toHaveBeenCalledOnce());
    expect(mocks.createSavedLineup.mock.calls[0]![0]).toMatchObject({
      coach: "Ács Ádám",
      team_leader: "Vezető Vera",
      ball_thrower: "Új Dobó",
    });
    expect(mocks.createSavedLineup.mock.calls[0]![0].assistant_coach).toBeUndefined();
  });

  it("keeps a cloned lineup's own staff over the defaults", async () => {
    renderCreator({
      staff: STAFF,
      initialValues: { ...emptyValues(), coach: "Klón Edző", team_leader: "" },
    });
    expect(await screen.findByRole("combobox", { name: "Coach" })).toHaveValue("Klón Edző");
    expect(screen.getByRole("combobox", { name: "Team leader (optional)" })).toHaveValue("");
  });
});

describe("LineupCreator unsaved changes", () => {
  it("guards the page from the first edit until the lineup is saved", async () => {
    const user = userEvent.setup();
    const { isDirty } = renderCreator();
    await screen.findByLabelText("Opponent");
    expect(isDirty()).toBe(false);
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    expect(isDirty()).toBe(true);
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await screen.findByText(/Saved\./);
    expect(isDirty()).toBe(false);
    await user.type(screen.getByLabelText("Match name (optional)"), "Final");
    expect(isDirty()).toBe(true);
  });

  it("keeps guarding when the save fails", async () => {
    mocks.createSavedLineup.mockRejectedValueOnce(new ApiError(503));
    const user = userEvent.setup();
    const { isDirty } = renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(isDirty()).toBe(true);
  });

  it("does not guard a clone that nobody has changed yet", async () => {
    const { isDirty } = renderCreator({ initialValues: { ...emptyValues(), division: "OB I." } });
    expect(await screen.findByLabelText("Division")).toHaveValue("OB I.");
    expect(isDirty()).toBe(false);
  });
});

describe("LineupCreator save", () => {
  it("saves roster players and a listed opponent by id, then offers the downloads", async () => {
    const user = userEvent.setup();
    const { invalidate } = renderCreator();
    await fillMatch(user, "Listed FC");
    await pick(1, "Kovács Anna");
    await user.type(within(slot(6)).getByLabelText("Name"), "Kiss Ádám");
    await user.type(within(slot(6)).getByLabelText("NSSZ number"), "MVLSZ9");
    await user.type(screen.getByLabelText("Doctor (optional)"), "Dr. Kis");
    await user.type(screen.getByLabelText("Location (optional, not printed)"), "Szeged");
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
      location: "Szeged",
      players: [
        { source_player_id: "p-ann", cap_number: 1 },
        { name: "Kiss Ádám", nssz_number: "MVLSZ9", cap_number: 6 },
      ],
    });
    expect(mocks.createSavedLineup.mock.calls[0]![0].players).toHaveLength(2);
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

  it("maps a 422 onto the fields it names, players by their cap row", async () => {
    const user = userEvent.setup();
    mocks.createSavedLineup.mockRejectedValue(
      new ApiError(422, {
        detail: [
          { loc: ["body", "opponent_name"], msg: "String should have at most 120 characters" },
          { loc: ["body", "players", 1, "source_player_id"], msg: "Value error, twice" },
          { loc: ["body", "players"], msg: "Value error, Cap numbers must be unique" },
          { loc: ["body", "cap"], msg: "Input should be 'Fehér' or 'Kék'" },
        ],
      }),
    );
    renderCreator();
    await fillMatch(user);
    await pick(1, "Nagy Bence");
    await pick(9, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));

    expect(
      await screen.findByText("String should have at most 120 characters"),
    ).toBeInTheDocument();
    // The second player sent is the one in cap row 9.
    expect(within(slot(9)).getByText("twice")).toBeInTheDocument();
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

describe("LineupCreator date and time", () => {
  /** Fills the match, picks a player and sets the date (and time, when given). */
  async function fillWithDate(user: User, date: string, time?: string) {
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    fireEvent.change(screen.getByLabelText("Date"), { target: { value: date } });
    if (time)
      fireEvent.change(screen.getByLabelText("Start time (optional)"), { target: { value: time } });
  }

  it("saves the date and time as structured fields and no printed text", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillWithDate(user, "2026-12-05", "18:30");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await waitFor(() => expect(mocks.createSavedLineup).toHaveBeenCalledOnce());
    const body = mocks.createSavedLineup.mock.calls[0]![0];
    expect(body).toMatchObject({ match_date: "2026-12-05", match_time: "18:30" });
    expect(body).not.toHaveProperty("date");
  });

  it("leaves the time out of the save when it is blank", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillWithDate(user, "2026-12-05");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    await waitFor(() => expect(mocks.createSavedLineup).toHaveBeenCalledOnce());
    expect(mocks.createSavedLineup.mock.calls[0]![0].match_time).toBeUndefined();
  });

  it("previews with the printed text, with and without the time", async () => {
    const user = userEvent.setup();
    renderCreator();
    await fillWithDate(user, "2026-12-05", "18:30");
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await waitFor(() => expect(mocks.generateLineup).toHaveBeenCalledOnce());
    expect(mocks.generateLineup.mock.calls[0]![0].date).toBe("2026. 12. 05. 18:30");
    fireEvent.change(screen.getByLabelText("Start time (optional)"), { target: { value: "" } });
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await waitFor(() => expect(mocks.generateLineup).toHaveBeenCalledTimes(2));
    expect(mocks.generateLineup.mock.calls[1]![0].date).toBe("2026. 12. 05.");
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
    // The file is handed to the panel, so the large view is on offer.
    expect(screen.getByRole("button", { name: "Enlarge" })).toBeInTheDocument();
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

/** A saved lineup to edit: Anna from the roster in cap 1, a typed-in player in cap 2. */
const EDITED: SavedLineup = {
  id: "s-1",
  team_id: TEAM_ID,
  team_name: "SZVTK",
  opponent_name: "Csongrád",
  match_name: "SZVTK - Csongrád",
  division: "OB I.",
  cap: "Kék",
  date: "2026. 10. 01. 18:30",
  match_date: "2026-10-01",
  match_time: "18:30:00",
  location: "Komjádi",
  coach: "Kovács Béla",
  doctor: null,
  assistant_coach: null,
  team_leader: null,
  ball_thrower: null,
  source_team_id: TEAM_ID,
  source_opponent_id: null,
  created_at: "2026-10-01T10:00:00Z",
  updated_at: "2026-10-01T10:00:00.123456Z",
  players: [
    {
      id: "x1",
      cap_number: 1,
      name: "Kovács Anna",
      nssz_number: "MVLSZ1",
      source_player_id: "p-ann",
    },
    { id: "x2", cap_number: 2, name: "Kézi Kata", nssz_number: "K2", source_player_id: null },
  ],
};

function renderEdit(lineup: SavedLineup = EDITED, onReload = vi.fn()) {
  const rendered = renderCreator({
    initialValues: valuesForEdit(lineup, [ANN, BEN]),
    edit: { lineup, onReload },
  });
  return { ...rendered, onReload };
}

describe("LineupCreator edit mode", () => {
  beforeEach(() => {
    mocks.updateSavedLineup.mockResolvedValue({
      ...EDITED,
      updated_at: "2026-11-24T09:00:00.000001Z",
    });
  });

  it("starts from the lineup, not dirty, with Save changes and Cancel", async () => {
    const { isDirty } = renderEdit();
    expect(await screen.findByLabelText("Opponent")).toHaveValue("Csongrád");
    expect(screen.getByLabelText("Match name (optional)")).toHaveValue("");
    expect(screen.getByLabelText("Date")).toHaveValue("2026-10-01");
    expect(screen.getByLabelText("Start time (optional)")).toHaveValue("18:30");
    expect(screen.getByLabelText("Location (optional, not printed)")).toHaveValue("Komjádi");
    expect(within(slot(2)).getByLabelText("Name")).toHaveValue("Kézi Kata");
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Save lineup" })).not.toBeInTheDocument();
    expect(isDirty()).toBe(false);
  });

  it("saves the changes in place with the loaded version, then with the saved one", async () => {
    const user = userEvent.setup();
    const { invalidate, isDirty } = renderEdit();
    await user.type(await screen.findByLabelText("Match name (optional)"), "Kupadöntő");
    expect(isDirty()).toBe(true);
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Changes saved")).toBeInTheDocument();
    expect(mocks.createSavedLineup).not.toHaveBeenCalled();
    const [id, body] = mocks.updateSavedLineup.mock.calls[0]!;
    expect(id).toBe("s-1");
    expect(body).toMatchObject({
      source_team_id: TEAM_ID,
      match_name: "Kupadöntő",
      opponent_name: "Csongrád",
      match_date: "2026-10-01",
      match_time: "18:30",
      location: "Komjádi",
      expected_updated_at: "2026-10-01T10:00:00.123456Z",
      players: [
        { source_player_id: "p-ann", cap_number: 1 },
        { name: "Kézi Kata", nssz_number: "K2", cap_number: 2 },
      ],
    });
    expect(body).not.toHaveProperty("team_id");
    expect(isDirty()).toBe(false);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["saved"] });
    expect(screen.getByRole("status")).toHaveTextContent(/Saved/);

    // A second edit is based on the version the first save returned.
    await user.type(screen.getByLabelText("Division"), " A");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(mocks.updateSavedLineup).toHaveBeenCalledTimes(2));
    expect(mocks.updateSavedLineup.mock.calls[1]![1]).toMatchObject({
      division: "OB I. A",
      expected_updated_at: "2026-11-24T09:00:00.000001Z",
    });
  });

  it("says someone else changed it on a 409, keeps the input and offers the latest version", async () => {
    const user = userEvent.setup();
    mocks.updateSavedLineup.mockRejectedValue(new ApiError(409, { detail: "changed" }));
    const { onReload, isDirty } = renderEdit();
    await user.type(await screen.findByLabelText("Division"), " A");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Someone else changed this lineup/);
    expect(alert).not.toHaveTextContent("changed\n");
    expect(screen.getByLabelText("Division")).toHaveValue("OB I. A");
    expect(isDirty()).toBe(true);
    expect(onReload).not.toHaveBeenCalled();
    await user.click(within(alert).getByRole("button", { name: /Load the latest version/ }));
    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it("says the lineup is gone when another member deleted it", async () => {
    const user = userEvent.setup();
    mocks.updateSavedLineup.mockRejectedValue(new SavedLineupGoneError());
    renderEdit();
    await user.click(await screen.findByRole("button", { name: "Save changes" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/no longer exists; another member may have deleted it/);
    expect(within(alert).getByRole("link", { name: "See saved lineups" })).toHaveAttribute(
      "href",
      "/saved",
    );
    expect(within(alert).queryByRole("button")).not.toBeInTheDocument();
  });

  it("keeps the generic text for a 404 of a player or opponent", async () => {
    const user = userEvent.setup();
    mocks.updateSavedLineup.mockRejectedValue(new ApiError(404));
    renderEdit();
    await user.click(await screen.findByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/That no longer exists/);
  });

  it("goes back to the Saved page on Cancel", async () => {
    const user = userEvent.setup();
    renderEdit();
    expect(screen.getByTestId("where")).toHaveTextContent("/");
    await user.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(screen.getByTestId("where")).toHaveTextContent("/saved");
  });

  it("previews with the lineup's own team when it is not the current team", async () => {
    const user = userEvent.setup();
    renderEdit({ ...EDITED, source_team_id: "other", team_name: "Másik SC" });
    await user.click(await screen.findByRole("button", { name: "Preview" }));
    await waitFor(() => expect(mocks.generateLineup).toHaveBeenCalled());
    expect(mocks.generateLineup.mock.calls[0]![0]).toMatchObject({ team_name: "Másik SC" });
  });

  it("previews with the current team's name when the lineup is the current team's", async () => {
    const user = userEvent.setup();
    renderEdit();
    await user.click(await screen.findByRole("button", { name: "Preview" }));
    await waitFor(() => expect(mocks.generateLineup).toHaveBeenCalled());
    expect(mocks.generateLineup.mock.calls[0]![0]).toMatchObject({ team_name: "SZVTK" });
  });
});

describe("LineupCreator new lineup", () => {
  it("has no Cancel and says Lineup saved", async () => {
    const user = userEvent.setup();
    renderCreator();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    await fillMatch(user);
    await pick(1, "Kovács Anna");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));
    expect(await screen.findByText("Lineup saved")).toBeInTheDocument();
    expect(mocks.updateSavedLineup).not.toHaveBeenCalled();
  });
});
