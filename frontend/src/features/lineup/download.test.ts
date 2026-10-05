import { afterEach } from "vitest";
import { filenameFromContentDisposition, saveFile } from "@/features/lineup/download";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("filenameFromContentDisposition", () => {
  it("prefers the UTF-8 filename* form so ő and ű survive", () => {
    const header = `attachment; filename="rajtlista_Hoeroe.pdf"; filename*=UTF-8''rajtlista_H%C5%91r%C5%91.pdf`;
    expect(filenameFromContentDisposition(header, "lineup.pdf")).toBe("rajtlista_Hőrő.pdf");
  });

  it("falls back to the plain ASCII filename", () => {
    expect(filenameFromContentDisposition('attachment; filename="sheet.docx"', "lineup.docx")).toBe(
      "sheet.docx",
    );
  });

  it("falls back to the plain name when filename* is malformed", () => {
    const header = `attachment; filename="plain.pdf"; filename*=UTF-8''%E0%A4%A`;
    expect(filenameFromContentDisposition(header, "lineup.pdf")).toBe("plain.pdf");
  });

  it("uses the fallback when there is no usable header", () => {
    expect(filenameFromContentDisposition(null, "lineup.pdf")).toBe("lineup.pdf");
    expect(filenameFromContentDisposition("attachment", "lineup.pdf")).toBe("lineup.pdf");
  });

  it("never lets a path or control characters into the download name", () => {
    const header = `attachment; filename*=UTF-8''..%2F..%2Fetc%2Fpasswd`;
    expect(filenameFromContentDisposition(header, "lineup.pdf")).toBe(".._.._etc_passwd");
  });
});

describe("saveFile", () => {
  it("clicks a temporary link to the blob and releases the object URL afterwards", () => {
    vi.useFakeTimers();
    const createObjectURL = vi.fn(() => "blob:fake");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      expect(this.download).toBe("sheet.pdf");
      expect(this.getAttribute("href")).toBe("blob:fake");
    });

    saveFile({ blob: new Blob(["x"]), filename: "sheet.pdf" });

    expect(click).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download]")).toBeNull();
    expect(revokeObjectURL).not.toHaveBeenCalled();
    vi.runAllTimers();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:fake");
    vi.unstubAllGlobals();
  });
});
