import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";
import { i18n } from "@/i18n";
import { ApiError } from "@/api/errors";
import { LineupForm, SLOW_PDF_NOTICE_MS } from "@/features/lineup/lineup-form";
import type { Staff } from "@/features/staff/api";
import { unsavedProbe } from "@/test/unsaved";

const { generateLineup, saveFile } = vi.hoisted(() => ({
  generateLineup: vi.fn(),
  saveFile: vi.fn(),
}));
vi.mock("@/features/lineup/generate", () => ({ generateLineup }));
vi.mock("@/features/lineup/download", () => ({ saveFile }));

function renderForm(staff?: Staff[]) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const unsaved = unsavedProbe();
  const view = render(
    <QueryClientProvider client={client}>
      <unsaved.Wrapper>
        <LineupForm staff={staff} />
      </unsaved.Wrapper>
    </QueryClientProvider>,
  );
  return { ...view, isDirty: unsaved.isDirty };
}

/** The row of one cap number. */
const capRow = (n: number) => screen.getByLabelText(`Cap no. ${n}`);

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  const values: Record<string, string> = {
    Match: "SZVTK - Csongrád",
    Division: "OB II.",
    "Team name": "SZVTK",
    Coach: "Coach",
    Doctor: "Doctor",
    "Assistant coach": "Assistant",
    "Team leader": "Leader",
    "Ball thrower": "Thrower",
  };
  // Pasting instead of typing keeps the 15-row form fast enough under coverage.
  for (const [label, value] of Object.entries(values)) {
    await user.click(screen.getByLabelText(label));
    await user.paste(value);
  }
  await user.click(within(capRow(1)).getByLabelText("Name"));
  await user.paste("Török András");
  await user.click(within(capRow(1)).getByLabelText("NSSZ number"));
  await user.paste("MVLSZ1");
}

beforeEach(() => {
  generateLineup.mockReset();
  saveFile.mockReset();
});
afterEach(() => vi.useRealTimers());

function staffEntry(name: string, role: Staff["role"], is_default = false): Staff {
  return {
    id: `st-${name}`,
    team_id: "t-1",
    role,
    name,
    source_player_id: null,
    is_default,
    created_at: "",
  };
}

describe("LineupForm staff pickers", () => {
  it("starts with each role's default, suggests the role's entries and keeps free text", async () => {
    generateLineup.mockResolvedValue({ blob: new Blob(["%PDF"]), filename: "sheet.pdf" });
    const user = userEvent.setup();
    const { isDirty } = renderForm([
      staffEntry("Edző Ede", "coach", true),
      staffEntry("Ács Ádám", "coach"),
      staffEntry("Segéd Sára", "assistant_coach", true),
    ]);
    const coach = screen.getByRole("combobox", { name: "Coach" });
    expect(coach).toHaveValue("Edző Ede");
    expect(screen.getByRole("combobox", { name: "Assistant coach" })).toHaveValue("Segéd Sára");
    expect(screen.getByRole("combobox", { name: "Team leader" })).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Doctor" })).toHaveValue("");
    expect(isDirty()).toBe(false);
    await user.click(coach);
    const list = screen.getByRole("listbox");
    expect(
      within(list)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Edző Ede", "Ács Ádám"]);
    await user.click(screen.getByRole("option", { name: "Ács Ádám" }));
    expect(coach).toHaveValue("Ács Ádám");
    await user.type(screen.getByRole("combobox", { name: "Team leader" }), "Új Vezető");
    for (const [label, value] of [
      ["Match", "SZVTK - Csongrád"],
      ["Division", "OB II."],
      ["Team name", "SZVTK"],
      ["Doctor", "Dr. Kis"],
      ["Ball thrower", "Dobó"],
    ]) {
      await user.click(screen.getByLabelText(label!));
      await user.paste(value!);
    }
    await user.click(within(capRow(1)).getByLabelText("Name"));
    await user.paste("Török András");
    await user.click(within(capRow(1)).getByLabelText("NSSZ number"));
    await user.paste("MVLSZ1");
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await vi.waitFor(() => expect(generateLineup).toHaveBeenCalledOnce());
    expect(generateLineup.mock.calls[0]![0]).toMatchObject({
      coach: "Ács Ádám",
      assistant_coach: "Segéd Sára",
      team_leader: "Új Vezető",
      ball_thrower: "Dobó",
      doctor: "Dr. Kis",
    });
  });
});

describe("LineupForm unsaved changes", () => {
  it("guards the page from the first edit until the sheet is downloaded", async () => {
    generateLineup.mockResolvedValue({ blob: new Blob(["%PDF"]), filename: "sheet.pdf" });
    const user = userEvent.setup();
    const { isDirty } = renderForm();
    expect(isDirty()).toBe(false);
    await fillValidForm(user);
    expect(isDirty()).toBe(true);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await vi.waitFor(() => expect(saveFile).toHaveBeenCalledOnce());
    await vi.waitFor(() => expect(isDirty()).toBe(false));
    await user.type(screen.getByLabelText("Match"), "!");
    expect(isDirty()).toBe(true);
  });

  it("keeps guarding when the download fails", async () => {
    generateLineup.mockRejectedValue(new ApiError(503));
    const user = userEvent.setup();
    const { isDirty } = renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(isDirty()).toBe(true);
  });
});

describe("LineupForm", () => {
  it("starts with the 15 empty cap rows in cap order and the white caps selected", () => {
    renderForm();
    expect(screen.getByLabelText("Cap colour")).toHaveValue("Fehér");
    const rows = screen.getAllByRole("group", { name: /^Cap no\./ });
    expect(rows.map((row) => row.getAttribute("aria-label"))).toEqual(
      Array.from({ length: 15 }, (_, i) => `Cap no. ${i + 1}`),
    );
    expect(within(capRow(15)).getByText("15")).toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add player/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear row 1" })).toBeDisabled();
    expect(screen.getByText("(0 of 15)")).toBeInTheDocument();
  });

  it("shows field errors and sends nothing when the form is empty", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await screen.findByText("Match is required")).toBeInTheDocument();
    expect(screen.getByLabelText("Match")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Add at least one player")).toBeInTheDocument();
    expect(screen.queryByText("Name is required")).not.toBeInTheDocument();
    expect(generateLineup).not.toHaveBeenCalled();
  });

  it("re-translates the errors on screen when the language changes", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await screen.findByText("Match is required")).toBeInTheDocument();
    await act(() => i18n.changeLanguage("hu"));
    expect(screen.getByText("Mérkőzés megadása kötelező")).toBeInTheDocument();
    expect(screen.getByText("Adjon hozzá legalább egy játékost")).toBeInTheDocument();
    expect(screen.getByLabelText("Mérkőzés")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "PDF letöltése" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Sapkaszám: 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1. sor ürítése" })).toBeInTheDocument();
  });

  it("shows cap colours in the current language but submits the Hungarian value", async () => {
    const user = userEvent.setup();
    renderForm();
    expect(screen.getByRole("option", { name: "White" })).toHaveValue("Fehér");
    await act(() => i18n.changeLanguage("hu"));
    expect(screen.getByRole("option", { name: "Kék" })).toHaveValue("Kék");
    await user.selectOptions(screen.getByLabelText("Sapka színe"), "Kék");
    expect(screen.getByLabelText("Sapka színe")).toHaveValue("Kék");
  });

  it("flags a half-filled row, and Clear empties it and drops its error", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillValidForm(user);
    await user.type(within(capRow(3)).getByLabelText("Name"), "Kiss Ádám");
    expect(screen.getByText("(2 of 15)")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await within(capRow(3)).findByText("NSSZ number is required")).toBeInTheDocument();
    expect(generateLineup).not.toHaveBeenCalled();

    const clear = screen.getByRole("button", { name: "Clear row 3" });
    await user.click(clear);
    expect(within(capRow(3)).getByLabelText("Name")).toHaveValue("");
    expect(within(capRow(3)).queryByText("NSSZ number is required")).not.toBeInTheDocument();
    expect(clear).toBeDisabled();
    expect(screen.getByText("(1 of 15)")).toBeInTheDocument();
  });

  it("submits the trimmed values as PDF and hands the file to the browser", async () => {
    const user = userEvent.setup();
    const file = { blob: new Blob(["x"]), filename: "sheet.pdf" };
    generateLineup.mockResolvedValue(file);
    renderForm();
    await fillValidForm(user);
    await user.type(within(capRow(7)).getByLabelText("Name"), "  Kiss Ádám ");
    await user.type(within(capRow(7)).getByLabelText("NSSZ number"), "MVLSZ7");
    await user.selectOptions(screen.getByLabelText("Cap colour"), "Kék");

    await user.click(screen.getByRole("button", { name: "Download PDF" }));

    expect(await screen.findByText("Downloaded sheet.pdf.")).toBeInTheDocument();
    expect(generateLineup).toHaveBeenCalledOnce();
    const [body, format] = generateLineup.mock.calls[0]!;
    expect(format).toBe("pdf");
    expect(body).toMatchObject({
      match: "SZVTK - Csongrád",
      cap: "Kék",
      coach: "Coach",
      players: [
        { cap_number: 1, name: "Török András", nssz_number: "MVLSZ1" },
        { cap_number: 7, name: "Kiss Ádám", nssz_number: "MVLSZ7" },
      ],
    });
    expect(saveFile).toHaveBeenCalledWith(file);
  });

  it("opens on today's local date with no time", () => {
    vi.useFakeTimers({ now: new Date(2026, 10, 24, 23, 59), toFake: ["Date"] });
    renderForm();
    expect(screen.getByLabelText("Date")).toHaveValue("2026-11-24");
    expect(screen.getByLabelText("Start time (optional)")).toHaveValue("");
  });

  it("requires a date and prints the chosen date and time on the sheet", async () => {
    const user = userEvent.setup();
    generateLineup.mockResolvedValue({ blob: new Blob(["x"]), filename: "sheet.pdf" });
    renderForm();
    await fillValidForm(user);
    await user.clear(screen.getByLabelText("Date"));
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await screen.findByText("Date is required")).toBeInTheDocument();
    expect(generateLineup).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Date"), { target: { value: "2026-12-05" } });
    fireEvent.change(screen.getByLabelText("Start time (optional)"), {
      target: { value: "18:30" },
    });
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await vi.waitFor(() => expect(generateLineup).toHaveBeenCalledOnce());
    expect(generateLineup.mock.calls[0]![0].date).toBe("2026. 12. 05. 18:30");
  });

  it("submits as DOCX from the second button", async () => {
    const user = userEvent.setup();
    generateLineup.mockResolvedValue({ blob: new Blob(["x"]), filename: "sheet.docx" });
    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download DOCX" }));
    expect(await screen.findByText("Downloaded sheet.docx.")).toBeInTheDocument();
    expect(generateLineup.mock.calls[0]![1]).toBe("docx");
  });

  it("disables both buttons while a request runs so it can't be sent twice", async () => {
    const user = userEvent.setup();
    let finish: (value: unknown) => void = () => {};
    generateLineup.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));

    const pdf = await screen.findByRole("button", { name: "Download PDF" });
    expect(pdf).toBeDisabled();
    expect(pdf).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("button", { name: "Download DOCX" })).toBeDisabled();

    await act(async () => finish({ blob: new Blob(["x"]), filename: "a.pdf" }));
    expect(await screen.findByRole("button", { name: "Download PDF" })).toBeEnabled();
    expect(generateLineup).toHaveBeenCalledOnce();
  });

  it("explains a slow PDF after 5 seconds, but not a slow DOCX", async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    vi.useFakeTimers({ shouldAdvanceTime: true });
    generateLineup.mockReturnValue(new Promise(() => {}));
    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));

    expect(screen.queryByText(/first one after a break/)).not.toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(SLOW_PDF_NOTICE_MS));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Generating the PDF — the first one after a break takes a bit longer.",
    );
  });

  it("maps a 422 onto the fields it names, players by their cap row", async () => {
    const user = userEvent.setup();
    generateLineup.mockRejectedValue(
      new ApiError(422, {
        detail: [
          { loc: ["body", "match"], msg: "String should have at most 200 characters" },
          { loc: ["body", "players", 1, "nssz_number"], msg: "Value error, taken" },
          { loc: ["body", "players"], msg: "Value error, Player cap numbers must be unique" },
          { loc: ["query", "format"], msg: "ignored" },
        ],
      }),
    );
    renderForm();
    await fillValidForm(user);
    await user.type(within(capRow(5)).getByLabelText("Name"), "Kiss Ádám");
    await user.type(within(capRow(5)).getByLabelText("NSSZ number"), "MVLSZ5");
    await user.click(screen.getByRole("button", { name: "Download PDF" }));

    expect(
      await screen.findByText("String should have at most 200 characters"),
    ).toBeInTheDocument();
    // The second player sent is the one in cap row 5.
    expect(within(capRow(5)).getByText("taken")).toBeInTheDocument();
    expect(screen.getByText("Player cap numbers must be unique")).toBeInTheDocument();
    expect(screen.getByText(/server rejected some of the details/i)).toBeInTheDocument();
    expect(saveFile).not.toHaveBeenCalled();
  });

  it.each([
    [new ApiError(0), /can't reach the server/i],
    [new ApiError(503), /busy or starting up/i],
    [new ApiError(504), /too long/i],
    [new ApiError(500), /went wrong on our side/i],
  ])("shows a readable message for %o", async (error, message) => {
    const user = userEvent.setup();
    generateLineup.mockRejectedValue(error);
    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download DOCX" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("keeps the entered values in memory only", async () => {
    const user = userEvent.setup();
    renderForm();
    await fillValidForm(user);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});
