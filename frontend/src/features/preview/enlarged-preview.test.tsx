import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EnlargedPreview } from "@/features/preview/enlarged-preview";

const viewer = vi.hoisted(() => ({ zoom: vi.fn() }));
vi.mock("@/features/preview/pdf-viewer", () => ({
  PdfViewer: ({ zoom }: { zoom: unknown }) => {
    viewer.zoom(zoom);
    return <p>the pages</p>;
  },
}));

const file = new Blob(["%PDF"]);

describe("EnlargedPreview", () => {
  it("shows the pages in a focusable scroll area, fitted to the width at first", () => {
    render(<EnlargedPreview open onClose={() => {}} title="Preview" file={file} />);
    expect(screen.getByRole("dialog", { name: "Preview (enlarged)" })).toBeInTheDocument();
    const area = screen.getByRole("region", { name: "Pages of the lineup sheet" });
    expect(area).toHaveAttribute("tabindex", "0");
    expect(area).toHaveTextContent("the pages");
    expect(viewer.zoom).toHaveBeenLastCalledWith("fit");
    expect(screen.getByRole("radio", { name: "Fit width" })).toBeChecked();
  });

  it("zooms to 100, 150 and 200 percent", async () => {
    render(<EnlargedPreview open onClose={() => {}} title="Preview" file={file} />);
    expect(screen.getByRole("radiogroup", { name: "Zoom" })).toBeInTheDocument();
    for (const [name, zoom] of [
      ["100 %", 1],
      ["150 %", 1.5],
      ["200 %", 2],
    ] as const) {
      await userEvent.click(screen.getByRole("radio", { name }));
      expect(viewer.zoom).toHaveBeenLastCalledWith(zoom);
    }
    await userEvent.click(screen.getByRole("radio", { name: "Fit width" }));
    expect(viewer.zoom).toHaveBeenLastCalledWith("fit");
  });

  it("closes from its own button", async () => {
    const onClose = vi.fn();
    render(<EnlargedPreview open onClose={onClose} title="Preview" file={file} />);
    await userEvent.click(screen.getByRole("button", { name: "Close the enlarged preview" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("mounts nothing while closed", () => {
    render(<EnlargedPreview open={false} onClose={() => {}} title="Preview" file={file} />);
    expect(screen.queryByText("the pages")).not.toBeInTheDocument();
  });
});
