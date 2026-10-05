import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach } from "vitest";
import { ApiError } from "@/api/errors";
import { LineupForm, SLOW_PDF_NOTICE_MS } from "@/features/lineup/lineup-form";

const { generateLineup, saveFile } = vi.hoisted(() => ({
  generateLineup: vi.fn(),
  saveFile: vi.fn(),
}));
vi.mock("@/features/lineup/generate", () => ({ generateLineup }));
vi.mock("@/features/lineup/download", () => ({ saveFile }));

function renderForm() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LineupForm />
    </QueryClientProvider>,
  );
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  const values: Record<string, string> = {
    Match: "SZVTK - Csongrád",
    Division: "OB II.",
    "Team name": "SZVTK",
    Date: "2024. 12. 21.",
    Coach: "Coach",
    Doctor: "Doctor",
    "Assistant coach": "Assistant",
    "Team leader": "Leader",
    "Ball thrower": "Thrower",
    Name: "Török András",
    "NSSZ number": "MVLSZ1",
  };
  for (const [label, value] of Object.entries(values)) {
    await user.type(screen.getByLabelText(label), value);
  }
}

beforeEach(() => {
  generateLineup.mockReset();
  saveFile.mockReset();
});
afterEach(() => vi.useRealTimers());

describe("LineupForm", () => {
  it("starts with one player row and the white caps selected", () => {
    renderForm();
    expect(screen.getByLabelText("Cap colour")).toHaveValue("Fehér");
    expect(screen.getByLabelText("Cap no.")).toHaveValue(1);
    expect(screen.getByRole("button", { name: "Remove player 1" })).toBeDisabled();
  });

  it("shows field errors and sends nothing when the form is empty", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    expect(await screen.findByText("Match is required")).toBeInTheDocument();
    expect(screen.getByLabelText("Match")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(generateLineup).not.toHaveBeenCalled();
  });

  it("adds players with the next free cap number, up to 15, and removes them", async () => {
    const user = userEvent.setup();
    renderForm();
    const add = screen.getByRole("button", { name: /Add player/ });
    await user.click(add);
    await user.click(add);
    expect(screen.getAllByLabelText("Cap no.").map((el) => (el as HTMLInputElement).value)).toEqual(
      ["1", "2", "3"],
    );

    await user.click(screen.getByRole("button", { name: "Remove player 2" }));
    expect(screen.getAllByLabelText("Cap no.").map((el) => (el as HTMLInputElement).value)).toEqual(
      ["1", "3"],
    );
    await user.click(add);
    expect(screen.getAllByLabelText("Cap no.").map((el) => (el as HTMLInputElement).value)).toEqual(
      ["1", "3", "2"],
    );

    for (let i = 0; i < 12; i++) await user.click(add);
    expect(screen.getAllByRole("group", { name: /^Player/ })).toHaveLength(15);
    expect(add).toBeDisabled();
  });

  it("submits the trimmed values as PDF and hands the file to the browser", async () => {
    const user = userEvent.setup();
    const file = { blob: new Blob(["x"]), filename: "sheet.pdf" };
    generateLineup.mockResolvedValue(file);
    renderForm();
    await fillValidForm(user);
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
      players: [{ cap_number: 1, name: "Török András", nssz_number: "MVLSZ1" }],
    });
    expect(saveFile).toHaveBeenCalledWith(file);
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

  it("maps a 422 onto the fields it names", async () => {
    const user = userEvent.setup();
    generateLineup.mockRejectedValue(
      new ApiError(422, {
        detail: [
          { loc: ["body", "match"], msg: "String should have at most 200 characters" },
          { loc: ["body", "players", 0, "nssz_number"], msg: "Value error, taken" },
          { loc: ["body", "players"], msg: "Value error, Player cap numbers must be unique" },
          { loc: ["query", "format"], msg: "ignored" },
        ],
      }),
    );
    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));

    expect(
      await screen.findByText("String should have at most 200 characters"),
    ).toBeInTheDocument();
    const row = screen.getByRole("group", { name: "Player 1" });
    expect(within(row).getByText("taken")).toBeInTheDocument();
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
