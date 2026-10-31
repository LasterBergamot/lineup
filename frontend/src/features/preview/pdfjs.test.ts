import { loadPdfjs } from "@/features/preview/pdfjs";

const options = vi.hoisted(() => ({ workerSrc: "" }));
vi.mock("pdfjs-dist", () => ({ GlobalWorkerOptions: options, getDocument: vi.fn() }));
vi.mock("pdfjs-dist/build/pdf.worker.min.mjs?url", () => ({ default: "/assets/pdf.worker.js" }));

describe("loadPdfjs", () => {
  it("points pdf.js at the bundled, same-origin worker", async () => {
    const pdfjs = await loadPdfjs();
    expect(options.workerSrc).toBe("/assets/pdf.worker.js");
    expect(pdfjs.getDocument).toBeDefined();
  });
});
