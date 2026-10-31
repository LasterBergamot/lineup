import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import { OpponentCombobox } from "@/features/creator/opponent/opponent-combobox";
import {
  findDirectoryMatch,
  MAX_OPPONENT_LENGTH,
  mergeOpponentOptions,
  SEARCH_DELAY_MS,
} from "@/features/creator/opponent/options";
import { i18n } from "@/i18n";
import { fakeAuthClient, fakeSession, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({ searchPool: vi.fn(), listRecentOpponents: vi.fn() }));
vi.mock("@/features/directory/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/directory/api")>()),
  searchPool: mocks.searchPool,
}));
vi.mock("@/features/creator/opponent/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/creator/opponent/api")>()),
  listRecentOpponents: mocks.listRecentOpponents,
}));

const OWN = "00000000-0000-4000-8000-000000000001";
const FTC = { id: "00000000-0000-4000-8000-000000000002", name: "FTC" };
const BVSC = { id: "00000000-0000-4000-8000-000000000003", name: "BVSC" };

/** Holds the value like a form would, and records every `onChange`. */
function Harness({
  onChange,
}: {
  onChange: (value: string, match?: { directoryId: string }) => void;
}) {
  const [value, setValue] = useState("");
  return useAuth().status === "signed-in" ? (
    <OpponentCombobox
      aria-label="Opponent"
      teamId={OWN}
      value={value}
      onChange={(next, match) => {
        setValue(next);
        onChange(next, match);
      }}
    />
  ) : null;
}

function renderCombobox(session = fakeSession()) {
  const onChange = vi.fn();
  render(
    <QueryClientProvider client={testQueryClient()}>
      <AuthProvider client={fakeAuthClient(session).client}>
        <Harness onChange={onChange} />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { onChange };
}

/** The `<option>`s of the datalist the input points at, as `value (label)`. */
function suggestions(): string[] {
  const input = screen.getByRole("combobox", { name: "Opponent" });
  const list = document.getElementById(input.getAttribute("list")!)!;
  return [...list.querySelectorAll("option")].map((o) => `${o.value} (${o.label})`);
}

beforeEach(() => {
  mocks.searchPool.mockReset();
  mocks.listRecentOpponents.mockReset();
  mocks.searchPool.mockResolvedValue([FTC, { id: OWN, name: "SZVTK" }]);
  mocks.listRecentOpponents.mockResolvedValue(["Csongrád", "ftc"]);
});

describe("OpponentCombobox", () => {
  it("suggests listed teams and recent opponents, never the own team, without duplicates", async () => {
    renderCombobox();
    await waitFor(() =>
      expect(suggestions()).toEqual(["FTC (Listed team)", "Csongrád (Recent opponent)"]),
    );
    expect(mocks.listRecentOpponents).toHaveBeenCalledWith(OWN);
    expect(mocks.searchPool).toHaveBeenCalledWith("", 20);
    const input = screen.getByRole("combobox", { name: "Opponent" });
    expect(input).toHaveAttribute("maxlength", String(MAX_OPPONENT_LENGTH));
    expect(input).toHaveAttribute("autocomplete", "off");
  });

  it("reports the directory id when the text is a listed team's name, free text otherwise", async () => {
    const { onChange } = renderCombobox();
    await waitFor(() => expect(suggestions()).toHaveLength(2));
    const input = screen.getByRole("combobox", { name: "Opponent" });
    await userEvent.type(input, "ftc");
    expect(onChange).toHaveBeenLastCalledWith("ftc", { directoryId: FTC.id });
    await userEvent.type(input, "x");
    expect(onChange).toHaveBeenLastCalledWith("ftcx", undefined);
  });

  it("searches the directory with the typed term after a pause", async () => {
    renderCombobox();
    await waitFor(() => expect(mocks.searchPool).toHaveBeenCalledTimes(1));
    mocks.searchPool.mockResolvedValue([BVSC]);
    await userEvent.type(screen.getByRole("combobox", { name: "Opponent" }), "  BV ");
    await waitFor(() => expect(mocks.searchPool).toHaveBeenLastCalledWith("BV", 20), {
      timeout: SEARCH_DELAY_MS * 4,
    });
    await waitFor(() =>
      expect(suggestions()).toEqual([
        "BVSC (Listed team)",
        "Csongrád (Recent opponent)",
        "ftc (Recent opponent)",
      ]),
    );
  });

  it("still works as a plain text field when the suggestions cannot be loaded", async () => {
    mocks.searchPool.mockRejectedValue(new Error("down"));
    mocks.listRecentOpponents.mockRejectedValue(new Error("down"));
    const { onChange } = renderCombobox();
    await waitFor(() => expect(mocks.listRecentOpponents).toHaveBeenCalled());
    await userEvent.type(screen.getByRole("combobox", { name: "Opponent" }), "Eger");
    expect(onChange).toHaveBeenLastCalledWith("Eger", undefined);
    expect(suggestions()).toEqual([]);
  });

  it("labels the suggestions in Hungarian", async () => {
    await act(() => i18n.changeLanguage("hu"));
    renderCombobox();
    await waitFor(() =>
      expect(suggestions()).toEqual(["FTC (Listázott csapat)", "Csongrád (Korábbi ellenfél)"]),
    );
  });
});

describe("mergeOpponentOptions", () => {
  it("keeps the directory entry (and its id) when a recent name matches it", () => {
    expect(mergeOpponentOptions([" FTC "], [FTC], OWN)).toEqual([
      { name: "FTC", source: "directory", directoryId: FTC.id },
    ]);
  });

  it("drops repeated recent names", () => {
    expect(mergeOpponentOptions(["Eger", "eger"], [], OWN)).toEqual([
      { name: "Eger", source: "recent" },
    ]);
  });
});

describe("findDirectoryMatch", () => {
  const options = mergeOpponentOptions(["Eger"], [FTC], OWN);

  it("matches a directory name trimmed and case-insensitively", () => {
    expect(findDirectoryMatch(options, "  ftc ")).toEqual({ directoryId: FTC.id });
  });

  it("never matches a recent name, which has no id", () => {
    expect(findDirectoryMatch(options, "Eger")).toBeUndefined();
  });
});
