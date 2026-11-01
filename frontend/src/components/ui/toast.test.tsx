import { act, fireEvent, render, screen } from "@testing-library/react";
import { i18n } from "@/i18n";
import { ToastProvider } from "@/components/ui/toast";
import { MAX_TOASTS, TOAST_MS, useToast, type ToastKind } from "@/components/ui/use-toast";

function Raise({
  kind = "success",
  message = "Lineup saved",
}: {
  kind?: ToastKind;
  message?: string;
}) {
  const toast = useToast();
  return <button onClick={() => toast(kind, message)}>{`raise ${message}`}</button>;
}

function renderToasts(...raisers: Parameters<typeof Raise>[0][]) {
  return render(
    <ToastProvider>
      {raisers.map((props) => (
        <Raise key={props.message} {...props} />
      ))}
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});
afterEach(() => {
  vi.useRealTimers();
});

const click = (name: string) => fireEvent.click(screen.getByRole("button", { name }));

describe("Toast", () => {
  it("shows a message in a labelled live region and dismisses itself after 5 s", () => {
    renderToasts({ message: "Lineup saved" });
    expect(screen.getByRole("region", { name: "Notifications" })).toHaveAttribute(
      "aria-live",
      "polite",
    );
    click("raise Lineup saved");
    expect(screen.getByText("Lineup saved")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(TOAST_MS - 1));
    expect(screen.getByText("Lineup saved")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(1));
    expect(screen.queryByText("Lineup saved")).not.toBeInTheDocument();
  });

  it("dismisses an info toast on its own too", () => {
    renderToasts({ kind: "info", message: "FYI" });
    click("raise FYI");
    act(() => void vi.advanceTimersByTime(TOAST_MS));
    expect(screen.queryByText("FYI")).not.toBeInTheDocument();
  });

  it("keeps an error until it is dismissed, and announces it as an alert", async () => {
    renderToasts({ kind: "error", message: "Went wrong" });
    click("raise Went wrong");
    expect(screen.getByRole("alert")).toHaveTextContent("Went wrong");
    act(() => void vi.advanceTimersByTime(60_000));
    expect(screen.getByText("Went wrong")).toBeInTheDocument();
    click("Dismiss");
    expect(screen.queryByText("Went wrong")).not.toBeInTheDocument();
  });

  it("pauses while the pointer is on it and resumes with the time that was left", () => {
    renderToasts({ message: "Hold" });
    click("raise Hold");
    act(() => void vi.advanceTimersByTime(3000));
    const card = screen.getByText("Hold").parentElement!;
    fireEvent.mouseEnter(card);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(screen.getByText("Hold")).toBeInTheDocument();
    fireEvent.mouseLeave(card);
    act(() => void vi.advanceTimersByTime(1999));
    expect(screen.getByText("Hold")).toBeInTheDocument();
    act(() => void vi.advanceTimersByTime(1));
    expect(screen.queryByText("Hold")).not.toBeInTheDocument();
  });

  it("pauses while keyboard focus is inside it", () => {
    renderToasts({ message: "Focus" });
    click("raise Focus");
    const card = screen.getByText("Focus").parentElement!;
    fireEvent.focus(card);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(screen.getByText("Focus")).toBeInTheDocument();
    fireEvent.blur(card);
    act(() => void vi.advanceTimersByTime(TOAST_MS));
    expect(screen.queryByText("Focus")).not.toBeInTheDocument();
  });

  it("stays paused while the pointer has left but keyboard focus is still on it", () => {
    renderToasts({ message: "Both" });
    click("raise Both");
    const card = screen.getByText("Both").parentElement!;
    fireEvent.focus(card);
    fireEvent.mouseEnter(card);
    fireEvent.mouseLeave(card);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(screen.getByText("Both")).toBeInTheDocument();
    fireEvent.blur(card);
    act(() => void vi.advanceTimersByTime(TOAST_MS));
    expect(screen.queryByText("Both")).not.toBeInTheDocument();
  });

  it("shows at most three, dropping the oldest", () => {
    const names = ["one", "two", "three", "four"];
    renderToasts(...names.map((message) => ({ message })));
    for (const name of names) click(`raise ${name}`);
    expect(MAX_TOASTS).toBe(3);
    expect(screen.queryByText("one")).not.toBeInTheDocument();
    for (const name of names.slice(1)) expect(screen.getByText(name)).toBeInTheDocument();
  });

  it("translates its own labels", async () => {
    await i18n.changeLanguage("hu");
    renderToasts({ message: "Mentve" });
    expect(screen.getByRole("region", { name: "Értesítések" })).toBeInTheDocument();
    click("raise Mentve");
    expect(screen.getByRole("button", { name: "Bezárás" })).toBeInTheDocument();
  });

  it("keeps nothing in browser storage", () => {
    renderToasts({ message: "Lineup saved" });
    click("raise Lineup saved");
    expect(localStorage.length + sessionStorage.length).toBe(0);
  });
});

describe("useToast", () => {
  it("must be used below the provider", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Raise />)).toThrow("useToast must be used inside <ToastProvider>");
    error.mockRestore();
  });

  it("is a stable function, so effects that depend on it do not re-run", async () => {
    const seen: unknown[] = [];
    function Probe() {
      seen.push(useToast());
      return null;
    }
    const { rerender } = render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    rerender(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );
    expect(new Set(seen).size).toBe(1);
  });
});
