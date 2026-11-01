import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog } from "@/components/ui/dialog";
import { Tabs } from "@/components/ui/tabs";
import { PdfViewer, type PdfZoom } from "@/features/preview/pdf-viewer";

/** The zoom choices, as the multiple of 100 % each draws (`"fit"` fills the width). */
const ZOOMS = { fit: "fit", "100": 1, "150": 1.5, "200": 2 } as const satisfies Record<
  string,
  PdfZoom
>;
type ZoomKey = keyof typeof ZOOMS;
const ZOOM_KEYS = Object.keys(ZOOMS) as ZoomKey[];

/**
 * The preview in a large view for checking small print (names, NSSZ numbers, cap numbers): a
 * near-full-screen dialog on a desktop, the whole screen on a phone, with a zoom control (fit
 * width, 100 %, 150 %, 200 %) above a scrollable page area. The pages are drawn at the size they
 * are shown, so the text stays sharp at every zoom. Only the area scrolls, never the page behind,
 * and it takes the keyboard focus so the arrow keys scroll it. The file is the same in-memory
 * `Blob` as the small preview: no URL, no storage. Closing it (button, Esc or a click on the
 * scrim) calls `onClose`, and focus returns to whatever opened it.
 */
export function EnlargedPreview({
  open,
  onClose,
  title,
  file,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  file: Blob;
}) {
  const { t } = useTranslation();
  const [zoom, setZoom] = useState<ZoomKey>("fit");

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t("preview.enlargedTitle", { title })}
      closeLabel={t("preview.closeEnlarged")}
      className="h-dvh max-h-none w-full max-w-none rounded-none border-0 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] md:h-[95dvh] md:w-[95vw] md:rounded-xl md:border [&>div]:h-full [&>div]:p-3 md:[&>div]:p-6"
    >
      <Tabs
        id="enlarged-zoom"
        kind="radio"
        label={t("preview.zoom")}
        value={zoom}
        onChange={setZoom}
        options={ZOOM_KEYS.map((key) => ({
          value: key,
          label: key === "fit" ? t("preview.zoomFit") : t("preview.zoomPercent", { percent: key }),
        }))}
      />
      <div
        // Scrollable regions have to be focusable (axe `scrollable-region-focusable`), which also
        // lets the arrow keys scroll. `pinch-zoom` keeps the browser's own pinch on a phone.
        role="region"
        tabIndex={0}
        aria-label={t("preview.pages")}
        className="min-h-0 flex-1 touch-pan-x touch-pan-y touch-pinch-zoom overflow-auto rounded-md bg-muted p-2"
      >
        <PdfViewer file={file} zoom={ZOOMS[zoom]} />
      </div>
    </Dialog>
  );
}
