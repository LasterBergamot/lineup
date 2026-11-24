import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { createMemoryRouter, Link, Outlet, useLocation } from "react-router";
import { RouterProvider } from "react-router/dom";
import { UnsavedChangesGuard } from "@/components/unsaved-changes-guard";
import { useUnsavedChangesGuard } from "@/lib/unsaved-changes";

/** A stand-in form: the checkbox is its dirty state, so a test can switch it on and off. */
function FakeForm({ name }: { name: string }) {
  const [dirty, setDirty] = useState(false);
  useUnsavedChangesGuard(dirty);
  return (
    <label>
      <input type="checkbox" checked={dirty} onChange={(e) => setDirty(e.target.checked)} />
      {name}
    </label>
  );
}

function Where() {
  const location = useLocation();
  return <p data-testid="where">{location.pathname + location.search}</p>;
}

function renderGuard({ forms = ["Form A"] }: { forms?: string[] } = {}) {
  const router = createMemoryRouter(
    [
      {
        element: (
          <UnsavedChangesGuard>
            <Link to="/other">Other page</Link>
            <Link to="/">This page</Link>
            <Where />
            <Outlet />
          </UnsavedChangesGuard>
        ),
        children: [
          {
            index: true,
            element: (
              <>
                {forms.map((name) => (
                  <FakeForm key={name} name={name} />
                ))}
              </>
            ),
          },
          { path: "other", element: <h1>Other</h1> },
        ],
      },
    ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

const where = () => screen.getByTestId("where").textContent;

/** Fires `beforeunload` the way a reload would and says whether the page asked to stay. */
function reloadIsHeld() {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

describe("UnsavedChangesGuard", () => {
  it("lets a navigation through and the page reload when nothing is dirty", async () => {
    renderGuard();
    expect(reloadIsHeld()).toBe(false);
    await userEvent.click(screen.getByRole("link", { name: "Other page" }));
    expect(screen.getByRole("heading", { name: "Other" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks before leaving with unsaved changes: Stay keeps the form, Discard leaves", async () => {
    renderGuard();
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));
    await userEvent.click(screen.getByRole("link", { name: "Other page" }));

    const dialog = await screen.findByRole("dialog", { name: "Discard changes?" });
    expect(dialog).toHaveAccessibleDescription(
      "You have changes that are not saved. If you leave this page, they are lost.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(where()).toBe("/");
    expect(screen.getByRole("checkbox", { name: "Form A" })).toBeChecked();

    await userEvent.click(screen.getByRole("link", { name: "Other page" }));
    await userEvent.click(await screen.findByRole("button", { name: "Discard" }));
    expect(await screen.findByRole("heading", { name: "Other" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // The form unmounted with the page, so the guard is off again.
    expect(reloadIsHeld()).toBe(false);
  });

  it("treats the dialog's close button as Stay", async () => {
    renderGuard();
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));
    await userEvent.click(screen.getByRole("link", { name: "Other page" }));
    await userEvent.click(await screen.findByRole("button", { name: "Stay on this page" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(where()).toBe("/");
  });

  it("holds a reload or tab close only while a form is dirty", async () => {
    renderGuard();
    const box = screen.getByRole("checkbox", { name: "Form A" });
    await userEvent.click(box);
    expect(reloadIsHeld()).toBe(true);
    await userEvent.click(box);
    expect(reloadIsHeld()).toBe(false);
  });

  it("does not ask when the link leads to the page already shown", async () => {
    const router = renderGuard();
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));
    await userEvent.click(screen.getByRole("link", { name: "This page" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });

  it("asks when only the query string or the router state would change", async () => {
    const router = renderGuard();
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));

    await act(() => router.navigate("/?tab=quick"));
    await userEvent.click(await screen.findByRole("button", { name: "Stay" }));
    expect(where()).toBe("/");

    await act(() => router.navigate("/", { state: { cloneFromId: "some-id" } }));
    expect(await screen.findByRole("dialog", { name: "Discard changes?" })).toBeInTheDocument();
  });

  it("watches every form on the page: one dirty form is enough", async () => {
    renderGuard({ forms: ["Form A", "Form B"] });
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Form B" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "Form A" }));
    expect(reloadIsHeld()).toBe(true);
    await userEvent.click(screen.getByRole("checkbox", { name: "Form B" }));
    expect(reloadIsHeld()).toBe(false);
    await userEvent.click(screen.getByRole("link", { name: "Other page" }));
    expect(screen.getByRole("heading", { name: "Other" })).toBeInTheDocument();
  });
});

describe("useUnsavedChangesGuard outside the guard", () => {
  it("does nothing, so a form can be rendered on its own", async () => {
    render(<FakeForm name="Alone" />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Alone" }));
    expect(reloadIsHeld()).toBe(false);
  });
});
