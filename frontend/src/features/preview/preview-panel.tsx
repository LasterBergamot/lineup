import { Maximize2, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EnlargedPreview } from "@/features/preview/enlarged-preview";
import { useMediaQuery } from "@/lib/use-media-query";

/** The `lg` breakpoint in px: from here up the preview is a side panel, below it a dialog. */
const SIDE_PANEL_QUERY = "(min-width: 1024px)";

/**
 * The frame around a preview: a modal dialog (full screen, with a focus trap and Esc to close) on
 * a phone, a sticky side panel from the `lg` breakpoint up (the parent lays out a second column
 * for it). The content, usually a {@link PdfViewer} or a status message, is passed in and mounted in
 * whichever frame fits (crossing the `lg` breakpoint remounts it, so the PDF is drawn again); the
 * title and close button live here. Without a screen to measure (a test DOM) it renders the side
 * panel. Pass the PDF as `file` once it exists and an Enlarge button appears that opens it in an
 * {@link EnlargedPreview} (a zoomable full-size view); without a file there is nothing to enlarge.
 */
export function PreviewPanel({
  title,
  onClose,
  file,
  children,
}: {
  title: string;
  onClose: () => void;
  file?: Blob;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const sidePanel = useMediaQuery(SIDE_PANEL_QUERY, true);
  const [enlarged, setEnlarged] = useState(false);

  const enlarge = file && (
    <Button type="button" variant="outline" size="sm" onClick={() => setEnlarged(true)}>
      <Maximize2 />
      {t("preview.enlarge")}
    </Button>
  );
  const enlargedView = file && (
    <EnlargedPreview open={enlarged} onClose={() => setEnlarged(false)} title={title} file={file} />
  );

  if (!sidePanel) {
    return (
      <>
        <Dialog
          open
          onClose={onClose}
          title={title}
          closeLabel={t("preview.close")}
          actions={enlarge}
          className="h-dvh max-h-none w-full max-w-none rounded-none border-0 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
        >
          {children}
        </Dialog>
        {enlargedView}
      </>
    );
  }
  return (
    <>
      <aside
        aria-label={title}
        className="sticky top-4 flex max-h-[calc(100vh-2rem)] flex-col gap-3 self-start overflow-y-auto rounded-xl border bg-card p-4 shadow-md"
      >
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{title}</h2>
          <div className="flex items-center gap-2">
            {enlarge}
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={t("preview.close")}
              onClick={onClose}
            >
              <X />
            </Button>
          </div>
        </div>
        {children}
      </aside>
      {enlargedView}
    </>
  );
}
