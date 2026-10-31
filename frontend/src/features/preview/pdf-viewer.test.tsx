import { render, screen, waitFor } from "@testing-library/react";
import { PdfViewer } from "@/features/preview/pdf-viewer";

const mocks = vi.hoisted(() => ({ loadPdfjs: vi.fn() }));
vi.mock("@/features/preview/pdfjs", () => mocks);

/** A stand-in file: jsdom's Blob has no `arrayBuffer()`. */
const fileOf = () => ({ arrayBuffer: async () => new ArrayBuffer(8) }) as unknown as Blob;

function fakePdf(pages: number, render = () => ({ promise: Promise.resolve() })) {
  const destroy = vi.fn();
  const getDocument = vi.fn(() => ({
    destroy,
    promise: Promise.resolve({
      numPages: pages,
      getPage: async () => ({
        getViewport: ({ scale }: { scale: number }) => ({
          width: 100 * scale,
          height: 140 * scale,
        }),
        render,
      }),
    }),
  }));
  mocks.loadPdfjs.mockResolvedValue({ getDocument });
  return { getDocument, destroy };
}

describe("PdfViewer", () => {
  beforeEach(() => {
    // Braces on purpose: a hook that returns the mock would have Vitest call it as a teardown.
    mocks.loadPdfjs.mockReset();
  });

  it("draws one canvas per page and drops the loading placeholder", async () => {
    const pdf = fakePdf(2);
    const { container } = render(<PdfViewer file={fileOf()} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    await waitFor(() => expect(container.querySelectorAll("canvas")).toHaveLength(2));
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(pdf.getDocument).toHaveBeenCalledOnce();
    expect(container.querySelector("canvas")).toHaveAttribute("width", "200");
  });

  it("releases the pdf.js document when it unmounts", async () => {
    const pdf = fakePdf(1);
    const { container, unmount } = render(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(container.querySelectorAll("canvas")).toHaveLength(1));
    unmount();
    expect(pdf.destroy).toHaveBeenCalled();
  });

  it("says so when the file cannot be read", async () => {
    mocks.loadPdfjs.mockRejectedValue(new Error("boom"));
    render(<PdfViewer file={fileOf()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The preview could not be shown");
  });

  it("stops quietly when it unmounts while a page is still loading", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    fakePdf(1, () => ({ promise: gate }));
    const { container, unmount } = render(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(container.querySelectorAll("canvas")).toHaveLength(1));
    unmount();
    release();
    await Promise.resolve();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not draw a page that arrives after the viewer unmounted", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const destroy = vi.fn();
    mocks.loadPdfjs.mockResolvedValue({
      getDocument: () => ({
        destroy,
        promise: Promise.resolve({
          numPages: 1,
          getPage: async () => {
            await gate;
            return { getViewport: vi.fn(), render: vi.fn() };
          },
        }),
      }),
    });
    const { container, unmount } = render(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(mocks.loadPdfjs).toHaveBeenCalled());
    unmount();
    release();
    await Promise.resolve();
    expect(container.querySelectorAll("canvas")).toHaveLength(0);
  });

  it("does not report an error that happens after it unmounted", async () => {
    let fail!: (reason: Error) => void;
    mocks.loadPdfjs.mockReturnValue(new Promise((_, reject) => (fail = reject)));
    const { unmount } = render(<PdfViewer file={fileOf()} />);
    unmount();
    fail(new Error("late"));
    await Promise.resolve();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("PdfViewer with a new file", () => {
  it("shows the loading placeholder again while the next file is read", async () => {
    fakePdf(1);
    const { container, rerender } = render(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    mocks.loadPdfjs.mockReturnValue(new Promise(() => {}));
    rerender(<PdfViewer file={fileOf()} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(container).toBeTruthy();
  });
});
