import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { loadPdfjs } from "@/features/preview/pdfjs";

/** Canvas pixels per PDF point: 2 stays sharp on a phone screen without a huge bitmap. */
const SCALE = 2;

/**
 * Draws every page of a PDF into stacked canvases, as wide as the space it is given. The file
 * stays in memory only: it is read from the `Blob`, never given a URL or stored, and the pdf.js
 * document is destroyed when the file changes or the viewer unmounts. If the file cannot be read
 * the viewer says so instead of staying blank.
 */
export function PdfViewer({ file }: { file: Blob }) {
  const { t } = useTranslation();
  const pagesRef = useRef<HTMLDivElement>(null);
  // The outcome is remembered with the file it belongs to, so a new file counts as loading again
  // without resetting state inside the effect.
  const [outcome, setOutcome] = useState<{ file: Blob; status: "ready" | "error" }>();
  const state = outcome?.file === file ? outcome.status : "loading";

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => void) | undefined;
    (async () => {
      try {
        const pdfjs = await loadPdfjs();
        const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) });
        destroy = () => void task.destroy();
        const pdf = await task.promise;
        const container = pagesRef.current!;
        container.replaceChildren();
        for (let number = 1; number <= pdf.numPages; number++) {
          const page = await pdf.getPage(number);
          if (cancelled) return;
          const viewport = page.getViewport({ scale: SCALE });
          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          canvas.className = "h-auto w-full border bg-white";
          container.append(canvas);
          await page.render({ canvas, viewport }).promise;
        }
        if (!cancelled) setOutcome({ file, status: "ready" });
      } catch {
        if (!cancelled) setOutcome({ file, status: "error" });
      }
    })();
    return () => {
      cancelled = true;
      destroy?.();
    };
  }, [file]);

  return (
    <div className="flex flex-col gap-3">
      {state === "loading" && (
        <div role="status" aria-busy="true" aria-label={t("common.loading")}>
          <Skeleton className="aspect-[1/1.414] w-full" />
        </div>
      )}
      {state === "error" && (
        <p
          role="alert"
          className="rounded-md border border-destructive bg-destructive-soft p-3 text-sm text-destructive-soft-foreground"
        >
          {t("preview.unreadable")}
        </p>
      )}
      <div ref={pagesRef} className="flex flex-col gap-3" />
    </div>
  );
}
