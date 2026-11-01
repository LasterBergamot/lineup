import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { loadPdfjs } from "@/features/preview/pdfjs";

/** How the sheet is sized: `"fit"` fills the width it is given, a number is a multiple of 100 %. */
export type PdfZoom = "fit" | number;

/** CSS pixels per PDF point at 100 % (96 dpi screen, 72 points per inch): an A4 page is 794 px. */
const CSS_PX_PER_POINT = 96 / 72;

/**
 * Largest canvas, in pixels, that is still drawn at full resolution. Mobile Safari refuses a
 * canvas above 16.7 million pixels, so a bigger request is drawn a little softer instead of blank.
 */
const MAX_CANVAS_PIXELS = 16_000_000;

/** A resize has to rest this long before the pages are drawn again (a window drag fires dozens). */
const RESIZE_DEBOUNCE_MS = 150;

/**
 * Draws every page of a PDF into stacked canvases, each drawn at the size it is shown: the canvas
 * has as many pixels as the screen has for it (CSS width times `devicePixelRatio`), so small print
 * stays sharp at every zoom instead of being a fixed bitmap stretched or shrunk. With
 * `zoom="fit"` (default) the pages fill the width the viewer is given and are drawn again, after
 * a short pause, when that width changes; a number draws them at that multiple of the natural
 * size and the parent scrolls. The file stays in memory only: it is read from the `Blob`, never
 * given a URL or stored, and the pdf.js document is destroyed when the file changes or the
 * viewer unmounts. If the file cannot be read the viewer says so instead of staying blank.
 */
export function PdfViewer({ file, zoom = "fit" }: { file: Blob; zoom?: PdfZoom }) {
  const { t } = useTranslation();
  const rootRef = useRef<HTMLDivElement>(null);
  const pagesRef = useRef<HTMLDivElement>(null);
  // The outcome is remembered with the file it belongs to, so a new file counts as loading again
  // without resetting state inside the effect.
  const [outcome, setOutcome] = useState<{ file: Blob; status: "ready" | "error" }>();
  const state = outcome?.file === file ? outcome.status : "loading";
  const [loaded, setLoaded] = useState<{ file: Blob; pdf: PDFDocumentProxy }>();
  const pdf = loaded?.file === file ? loaded.pdf : undefined;
  // Width available for the pages; unknown (undefined) until the first measurement, and always
  // unknown without a layout engine (a test DOM), where the natural size is drawn.
  const [width, setWidth] = useState<number>();
  const fitWidth = zoom === "fit" ? width : undefined;

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let measured = false;
    const observer = new ResizeObserver(([entry]) => {
      const next = Math.round(entry!.contentRect.width);
      clearTimeout(timer);
      if (!measured) {
        measured = true;
        setWidth(next);
      } else {
        timer = setTimeout(() => setWidth(next), RESIZE_DEBOUNCE_MS);
      }
    });
    observer.observe(rootRef.current!);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => void) | undefined;
    (async () => {
      try {
        const pdfjs = await loadPdfjs();
        const task = pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) });
        destroy = () => void task.destroy();
        const loadedPdf = await task.promise;
        if (!cancelled) setLoaded({ file, pdf: loadedPdf });
      } catch {
        if (!cancelled) setOutcome({ file, status: "error" });
      }
    })();
    return () => {
      cancelled = true;
      destroy?.();
    };
  }, [file]);

  useEffect(() => {
    if (!pdf) return;
    let cancelled = false;
    let rendering: RenderTask | undefined;
    (async () => {
      try {
        const container = pagesRef.current!;
        while (container.children.length > pdf.numPages) container.lastElementChild!.remove();
        for (let number = 1; number <= pdf.numPages; number++) {
          const page = await pdf.getPage(number);
          if (cancelled) return;
          const natural = page.getViewport({ scale: 1 });
          const cssWidth =
            fitWidth ?? natural.width * CSS_PX_PER_POINT * (zoom === "fit" ? 1 : zoom);
          let scale = (cssWidth / natural.width) * window.devicePixelRatio;
          const pixels = natural.width * natural.height * scale * scale;
          if (pixels > MAX_CANVAS_PIXELS) scale *= Math.sqrt(MAX_CANVAS_PIXELS / pixels);
          const viewport = page.getViewport({ scale });
          // A fresh canvas replaces the old one once drawn, so a zoom or resize never flashes blank.
          const canvas = document.createElement("canvas");
          canvas.width = Math.round(viewport.width);
          canvas.height = Math.round(viewport.height);
          canvas.className = "h-auto max-w-none shrink-0 border bg-white";
          canvas.style.width = zoom === "fit" ? "100%" : `${cssWidth}px`;
          rendering = page.render({ canvas, viewport });
          await rendering.promise;
          const previous = container.children[number - 1];
          if (previous) previous.replaceWith(canvas);
          else container.append(canvas);
        }
        if (!cancelled) setOutcome({ file, status: "ready" });
      } catch {
        if (!cancelled) setOutcome({ file, status: "error" });
      }
    })();
    return () => {
      cancelled = true;
      rendering?.cancel();
    };
  }, [file, pdf, zoom, fitWidth]);

  return (
    <div ref={rootRef} className="flex flex-col gap-3">
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
