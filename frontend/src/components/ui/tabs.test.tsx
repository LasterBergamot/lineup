import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Tabs } from "@/components/ui/tabs";

const OPTIONS = [
  { value: "a", label: "Alpha" },
  { value: "b", label: "Beta" },
  { value: "c", label: "Gamma" },
] as const;

function Harness({ kind }: { kind?: "tab" | "radio" }) {
  const [value, setValue] = useState<"a" | "b" | "c">("a");
  return (
    <Tabs id="t" label="Letters" options={OPTIONS} value={value} onChange={setValue} kind={kind} />
  );
}

describe("Tabs as tabs", () => {
  it("is a tablist with the selected tab marked and in the tab order", () => {
    render(<Harness />);
    expect(screen.getByRole("tablist", { name: "Letters" })).toBeInTheDocument();
    const alpha = screen.getByRole("tab", { name: "Alpha" });
    expect(alpha).toHaveAttribute("aria-selected", "true");
    expect(alpha).toHaveAttribute("aria-controls", "t-panel");
    expect(alpha).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("tabindex", "-1");
  });

  it("selects on click", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("tab", { name: "Beta" }));
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("aria-selected", "true");
  });

  it("moves with the arrow keys, wrapping round, and with Home and End", async () => {
    render(<Harness />);
    screen.getByRole("tab", { name: "Alpha" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{ArrowDown}{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Gamma" })).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Gamma" })).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveFocus();
  });

  it("ignores other keys", async () => {
    render(<Harness />);
    screen.getByRole("tab", { name: "Alpha" }).focus();
    await userEvent.keyboard("x");
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("Tabs as radios", () => {
  it("is a radiogroup with aria-checked and no panel", async () => {
    render(<Harness kind="radio" />);
    expect(screen.getByRole("radiogroup", { name: "Letters" })).toBeInTheDocument();
    const alpha = screen.getByRole("radio", { name: "Alpha" });
    expect(alpha).toBeChecked();
    expect(alpha).not.toHaveAttribute("aria-controls");
    expect(alpha).not.toHaveAttribute("aria-selected");
    await userEvent.click(screen.getByRole("radio", { name: "Gamma" }));
    expect(screen.getByRole("radio", { name: "Gamma" })).toBeChecked();
  });
});
