import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";

function Harness({ description }: { description?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>Open it</button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="Hello"
        description={description}
        closeLabel="Close it"
      >
        <p>inside</p>
      </Dialog>
    </>
  );
}

describe("Dialog", () => {
  it("renders nothing while closed, and is named by its title once open", async () => {
    render(<Harness description="Some detail" />);
    expect(screen.queryByText("inside")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open it" }));
    const dialog = screen.getByRole("dialog", { name: "Hello" });
    expect(dialog).toHaveAttribute("open");
    expect(dialog).toHaveAccessibleDescription("Some detail");
    expect(screen.getByText("inside")).toBeInTheDocument();
  });

  it("has no description when none is given", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Open it" }));
    expect(screen.getByRole("dialog")).not.toHaveAttribute("aria-describedby");
  });

  it("closes with its button and gives focus back to the trigger", async () => {
    render(<Harness />);
    const trigger = screen.getByRole("button", { name: "Open it" });
    await userEvent.click(trigger);
    await userEvent.click(screen.getByRole("button", { name: "Close it" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes on Esc (the native close event)", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Open it" }));
    screen.getByRole("dialog").dispatchEvent(new Event("close"));
    expect(await screen.findByRole("button", { name: "Open it" })).toBeInTheDocument();
    expect(screen.queryByText("inside")).not.toBeInTheDocument();
  });

  it("closes on a click on the scrim but not on a click inside", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Open it" }));
    await userEvent.click(screen.getByText("inside"));
    expect(screen.getByText("inside")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("dialog"));
    expect(screen.queryByText("inside")).not.toBeInTheDocument();
  });

  it("gives focus back to the opener when its owner unmounts it while open", async () => {
    function Owner() {
      const [shown, setShown] = useState(false);
      return (
        <>
          <button onClick={() => setShown(true)}>Show</button>
          {shown && <Dialog open onClose={() => setShown(false)} title="T" closeLabel="Close it" />}
        </>
      );
    }
    render(<Owner />);
    const trigger = screen.getByRole("button", { name: "Show" });
    await userEvent.click(trigger);
    await userEvent.click(screen.getByRole("button", { name: "Close it" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("unmounts quietly when it was never opened", () => {
    const { unmount } = render(<Dialog open={false} onClose={() => {}} title="T" closeLabel="x" />);
    expect(() => unmount()).not.toThrow();
  });

  it("does not call onClose again for a close it caused itself", async () => {
    const onClose = vi.fn();
    const { rerender } = render(<Dialog open onClose={onClose} title="T" closeLabel="Close it" />);
    const dialog = screen.getByRole("dialog");
    rerender(<Dialog open={false} onClose={onClose} title="T" closeLabel="Close it" />);
    dialog.dispatchEvent(new Event("close"));
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("Dialog actions", () => {
  it("shows header actions next to the close button", () => {
    render(
      <Dialog open onClose={() => {}} title="T" closeLabel="Close" actions={<button>Extra</button>}>
        body
      </Dialog>,
    );
    expect(screen.getByRole("button", { name: "Extra" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
  });
});
