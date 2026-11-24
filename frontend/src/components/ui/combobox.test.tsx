import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Combobox, type ComboboxOption } from "@/components/ui/combobox";

const OPTIONS: ComboboxOption[] = [
  { value: "a", label: "Szűcs Anna", hint: "N-100" },
  { value: "b", label: "Nagy Bence", hint: "N-200", disabled: true },
  { value: "c", label: "Tóth Csaba", hint: "N-300" },
  { value: "d", label: "Varga Dóra" },
];

function Harness({ onPick }: { onPick?: (value: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <form onSubmit={(event) => event.preventDefault()}>
      <label htmlFor="picker">Player</label>
      <Combobox
        id="picker"
        options={OPTIONS}
        value={value}
        onChange={(next) => {
          setValue(next);
          onPick?.(next);
        }}
        emptyLabel="By hand"
        noMatchesLabel="Nobody"
      />
      <button type="submit">Submit</button>
    </form>
  );
}

const combobox = () => screen.getByRole("combobox", { name: "Player" });
const optionNames = () => screen.queryAllByRole("option").map((o) => o.textContent);

describe("Combobox", () => {
  it("is a collapsed combobox until clicked, then lists the empty choice and every option", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
    expect(combobox()).toHaveAttribute("placeholder", "By hand");
    expect(optionNames()).toEqual([]);
    await user.click(combobox());
    expect(combobox()).toHaveAttribute("aria-expanded", "true");
    expect(optionNames()).toEqual([
      "By hand",
      "Szűcs AnnaN-100",
      "Nagy BenceN-200",
      "Tóth CsabaN-300",
      "Varga Dóra",
    ]);
    // A second click closes it again.
    await user.click(combobox());
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
  });

  it("filters without regard to case or accents, and by the hint", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.type(combobox(), "SZUCS");
    expect(optionNames()).toEqual(["By hand", "Szűcs AnnaN-100"]);
    await user.clear(combobox());
    await user.type(combobox(), "n-300");
    expect(optionNames()).toEqual(["By hand", "Tóth CsabaN-300"]);
  });

  it("says so when nothing matches, and Enter then picks the empty choice at most", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    render(<Harness onPick={onPick} />);
    await user.type(combobox(), "zzz");
    expect(screen.getByRole("status")).toHaveTextContent("Nobody");
    expect(optionNames()).toEqual(["By hand"]);
    await user.keyboard("{Enter}");
    expect(onPick).toHaveBeenCalledWith("");
  });

  it("picks with the keyboard: arrows skip disabled options, Enter picks and never submits", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn((event: Event) => event.preventDefault());
    const onPick = vi.fn();
    const { container } = render(<Harness onPick={onPick} />);
    container.querySelector("form")!.addEventListener("submit", onSubmit);
    await user.click(combobox());
    await user.keyboard("{ArrowDown}"); // empty -> Szűcs
    await user.keyboard("{ArrowDown}"); // skips the disabled Nagy -> Tóth
    expect(combobox()).toHaveAttribute(
      "aria-activedescendant",
      screen.getByText("Tóth Csaba").closest("li")!.id,
    );
    await user.keyboard("{ArrowUp}{ArrowUp}{ArrowUp}{ArrowUp}"); // stops at the empty choice
    await user.keyboard("{End}");
    expect(combobox()).toHaveAttribute(
      "aria-activedescendant",
      screen.getByText("Varga Dóra").closest("li")!.id,
    );
    await user.keyboard("{ArrowDown}"); // stays at the end
    await user.keyboard("{Home}{ArrowDown}{Enter}");
    expect(onPick).toHaveBeenLastCalledWith("a");
    expect(combobox()).toHaveValue("Szűcs Anna");
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
    expect(onSubmit).not.toHaveBeenCalled();
    // Enter on a closed list does nothing either.
    await user.keyboard("{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
    expect(onPick).toHaveBeenCalledTimes(1);
  });

  it("opens from the arrow keys on the current choice, and Home/End move the cursor when closed", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(combobox());
    await user.click(screen.getByRole("option", { name: /^Tóth/ }));
    await user.keyboard("{Home}{End}");
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
    await user.keyboard("{ArrowDown}");
    expect(combobox()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("option", { name: /^Tóth/ })).toHaveAttribute("aria-selected", "true");
    expect(combobox()).toHaveAttribute(
      "aria-activedescendant",
      screen.getByRole("option", { name: /^Tóth/ }).id,
    );
    await user.keyboard("{Escape}");
    await user.keyboard("{ArrowUp}");
    expect(combobox()).toHaveAttribute("aria-expanded", "true");
  });

  it("Esc closes the list and drops the typed text; other keys leave it alone", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(combobox());
    await user.click(combobox()); // closed again
    await user.keyboard("{Escape}"); // nothing open: a no-op
    await user.type(combobox(), "tó");
    await user.keyboard("{Escape}");
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
    expect(combobox()).toHaveValue("");
  });

  it("closes when focus leaves, and does not pick a disabled option by click", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    render(<Harness onPick={onPick} />);
    await user.click(combobox());
    await user.click(screen.getByRole("option", { name: /^Nagy/ }));
    expect(onPick).not.toHaveBeenCalled();
    expect(combobox()).toHaveAttribute("aria-expanded", "true");
    await user.tab();
    expect(combobox()).toHaveAttribute("aria-expanded", "false");
  });
});
