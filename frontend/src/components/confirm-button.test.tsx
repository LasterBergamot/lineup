import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmButton } from "@/components/confirm-button";

function setup(loading = false) {
  const onConfirm = vi.fn();
  render(
    <ConfirmButton
      label="Remove"
      confirmLabel="Yes, remove"
      ariaLabel="Remove Ann"
      onConfirm={onConfirm}
      loading={loading}
    />,
  );
  return onConfirm;
}

describe("ConfirmButton", () => {
  it("does nothing on the first click except ask", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Remove Ann" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Yes, remove" })).toBeInTheDocument();
  });

  it("acts only on the confirming click", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Remove Ann" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, remove" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("goes back to the plain button on cancel", async () => {
    const onConfirm = setup();
    await userEvent.click(screen.getByRole("button", { name: "Remove Ann" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("button", { name: "Remove Ann" })).toBeInTheDocument();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("disables the confirming button while the request runs", async () => {
    setup(true);
    await userEvent.click(screen.getByRole("button", { name: "Remove Ann" }));
    expect(screen.getByRole("button", { name: "Yes, remove" })).toBeDisabled();
  });
});
