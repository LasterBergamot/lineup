import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreviewPanel } from "@/features/preview/preview-panel";

vi.mock("@/features/preview/enlarged-preview", () => ({
  EnlargedPreview: ({ open, onClose }: { open: boolean; onClose: () => void }) =>
    open ? (
      <div role="dialog" aria-label="Enlarged">
        <button onClick={onClose}>Back</button>
      </div>
    ) : null,
}));

const file = new Blob(["%PDF"]);

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

describe("PreviewPanel enlarging", () => {
  it("has no Enlarge button until there is a file", () => {
    render(
      <PreviewPanel title="Preview" onClose={() => {}}>
        <p>loading</p>
      </PreviewPanel>,
    );
    expect(screen.queryByRole("button", { name: "Enlarge" })).not.toBeInTheDocument();
  });

  it("opens and closes the large view from the side panel", async () => {
    render(
      <PreviewPanel title="Preview" onClose={() => {}} file={file}>
        <p>the sheet</p>
      </PreviewPanel>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Enlarge" }));
    expect(screen.getByRole("dialog", { name: "Enlarged" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
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

  it("offers Enlarge in the dialog header", async () => {
    window.matchMedia = vi.fn(() => ({
      matches: false,
      addEventListener: () => {},
      removeEventListener: () => {},
    })) as unknown as typeof window.matchMedia;
    render(
      <PreviewPanel title="Preview" onClose={() => {}} file={file}>
        <p>the sheet</p>
      </PreviewPanel>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Enlarge" }));
    expect(screen.getByRole("dialog", { name: "Enlarged" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.queryByRole("dialog", { name: "Enlarged" })).not.toBeInTheDocument();
  });
});
