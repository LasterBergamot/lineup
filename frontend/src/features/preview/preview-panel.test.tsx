import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreviewPanel } from "@/features/preview/preview-panel";

describe("PreviewPanel", () => {
  it("shows its title and content and closes on request", async () => {
    const onClose = vi.fn();
    render(
      <PreviewPanel title="Preview" onClose={onClose}>
        <p>the sheet</p>
      </PreviewPanel>,
    );
    expect(screen.getByRole("complementary", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByText("the sheet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close the preview" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});

describe("PreviewPanel on a phone", () => {
  afterEach(() => {
    Reflect.deleteProperty(window, "matchMedia");
  });

  it("is a modal dialog with the same title, content and close button", async () => {
    window.matchMedia = vi.fn(() => ({
      matches: false,
      addEventListener: () => {},
      removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    const onClose = vi.fn();
    render(
      <PreviewPanel title="Preview" onClose={onClose}>
        <p>the sheet</p>
      </PreviewPanel>,
    );
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByText("the sheet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Close the preview" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
