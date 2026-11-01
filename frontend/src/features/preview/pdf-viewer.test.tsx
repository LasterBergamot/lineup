import { act, render, screen, waitFor } from "@testing-library/react";
import { PdfViewer } from "@/features/preview/pdf-viewer";

const mocks = vi.hoisted(() => ({ loadPdfjs: vi.fn() }));
vi.mock("@/features/preview/pdfjs", () => mocks);

/** A stand-in file: jsdom's Blob has no `arrayBuffer()`. */
const fileOf = () => ({ arrayBuffer: async () => new ArrayBuffer(8) }) as unknown as Blob;

function fakePdf(
  pages: number,
  render: () => { promise: Promise<void>; cancel?: () => void } = () => ({
    promise: Promise.resolve(),
  }),
) {
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
        render: () => ({ cancel: () => {}, ...render() }),
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
    // No layout in jsdom: drawn at the natural size, 100 pt = 133 CSS px, at devicePixelRatio 1.
    expect(container.querySelector("canvas")).toHaveAttribute("width", "133");
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
    const drawPage = vi.fn(() => ({ promise: gate }));
    fakePdf(1, drawPage);
    const { container, unmount } = render(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(drawPage).toHaveBeenCalled());
    unmount();
    release();
    await Promise.resolve();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(container.querySelectorAll("canvas")).toHaveLength(0);
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

describe("PdfViewer sharpness", () => {
  const canvasesOf = (container: HTMLElement) => Array.from(container.querySelectorAll("canvas"));

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  /** A ResizeObserver whose callback the test calls itself; `width` is what it reports. */
  function stubResizeObserver() {
    const observers: Array<{
      report: (width: number) => void;
      disconnect: ReturnType<typeof vi.fn>;
    }> = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        disconnect = vi.fn();
        constructor(callback: (entries: Array<{ contentRect: { width: number } }>) => void) {
          observers.push({
            report: (width) => callback([{ contentRect: { width } }]),
            disconnect: this.disconnect,
          });
        }
        observe() {}
      },
    );
    return observers;
  }

  it("draws the canvas with as many pixels as the screen has for it", async () => {
    vi.stubGlobal("devicePixelRatio", 2);
    const observers = stubResizeObserver();
    fakePdf(1);
    const { container } = render(<PdfViewer file={fileOf()} />);
    act(() => observers[0]!.report(300));
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(1));
    const canvas = canvasesOf(container)[0]!;
    // 300 CSS px wide at a pixel ratio of 2 -> 600 canvas pixels, shown at the full width.
    expect(canvas).toHaveAttribute("width", "600");
    expect(canvas).toHaveAttribute("height", "840");
    expect(canvas.style.width).toBe("100%");
  });

  it("draws a numbered zoom at that multiple of the natural size, wider than the viewer", async () => {
    fakePdf(1);
    const { container } = render(<PdfViewer file={fileOf()} zoom={2} />);
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(1));
    const canvas = canvasesOf(container)[0]!;
    // 100 pt at 200 % = 100 * 96/72 * 2 CSS px.
    expect(parseFloat(canvas.style.width)).toBeCloseTo(266.67, 1);
    expect(canvas).toHaveAttribute("width", "267");
  });

  it("draws a huge request a little softer instead of past the canvas limit", async () => {
    vi.stubGlobal("devicePixelRatio", 15);
    fakePdf(1);
    const { container } = render(<PdfViewer file={fileOf()} zoom={2} />);
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(1));
    const canvas = canvasesOf(container)[0]!;
    expect(
      Number(canvas.getAttribute("width")) * Number(canvas.getAttribute("height")),
    ).toBeLessThanOrEqual(16_000_000 * 1.001);
  });

  it("draws again at the new size when the zoom changes, replacing the old canvas", async () => {
    fakePdf(1);
    const file = fileOf();
    const { container, rerender } = render(<PdfViewer file={file} zoom={1} />);
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(1));
    const first = canvasesOf(container)[0]!;
    expect(first).toHaveAttribute("width", "133");
    rerender(<PdfViewer file={file} zoom={1.5} />);
    await waitFor(() => expect(canvasesOf(container)[0]).not.toBe(first));
    expect(canvasesOf(container)).toHaveLength(1);
    expect(canvasesOf(container)[0]).toHaveAttribute("width", "200");
  });

  it("draws again after the width has rested, not on every resize event", async () => {
    const observers = stubResizeObserver();
    const pdf = fakePdf(1);
    const { container } = render(<PdfViewer file={fileOf()} />);
    act(() => observers[0]!.report(300));
    await waitFor(() => expect(canvasesOf(container)[0]).toHaveAttribute("width", "300"));
    expect(pdf.getDocument).toHaveBeenCalledOnce();

    vi.useFakeTimers();
    act(() => observers[0]!.report(350));
    act(() => observers[0]!.report(400));
    act(() => void vi.advanceTimersByTime(149));
    expect(canvasesOf(container)[0]).toHaveAttribute("width", "300");
    await act(async () => void vi.advanceTimersByTime(1));
    vi.useRealTimers();
    await waitFor(() => expect(canvasesOf(container)[0]).toHaveAttribute("width", "400"));
    // Only the newest width counts, and the document is read once.
    expect(pdf.getDocument).toHaveBeenCalledOnce();
  });

  it("stops watching the width when it unmounts", () => {
    const observers = stubResizeObserver();
    fakePdf(1);
    const { unmount } = render(<PdfViewer file={fileOf()} />);
    unmount();
    expect(observers[0]!.disconnect).toHaveBeenCalled();
  });

  it("cancels a page that is still being drawn when the zoom changes, without an error", async () => {
    // Like pdf.js: cancelling rejects the render promise.
    let abort!: (reason: Error) => void;
    const cancel = vi.fn(() => abort(new Error("cancelled")));
    fakePdf(1, () => ({ promise: new Promise<void>((_, reject) => (abort = reject)), cancel }));
    const file = fileOf();
    const { rerender } = render(<PdfViewer file={file} zoom={1} />);
    await waitFor(() => expect(abort).toBeDefined());
    rerender(<PdfViewer file={file} zoom={2} />);
    await waitFor(() => expect(cancel).toHaveBeenCalled());
    await Promise.resolve();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("drops the canvases a shorter next file no longer has", async () => {
    fakePdf(3);
    const first = fileOf();
    const { container, rerender } = render(<PdfViewer file={first} />);
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(3));
    fakePdf(1);
    rerender(<PdfViewer file={fileOf()} />);
    await waitFor(() => expect(canvasesOf(container)).toHaveLength(1));
  });

  it("says so when a page cannot be drawn", async () => {
    fakePdf(1, () => ({ promise: Promise.reject(new Error("bad page")) }));
    render(<PdfViewer file={fileOf()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The preview could not be shown");
  });
});
