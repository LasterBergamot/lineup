import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

/**
 * The frame around a preview: a full-screen sheet on a phone, a sticky side panel from the `lg`
 * breakpoint up (the parent lays out a second column for it). The content, usually a
 * {@link PdfViewer} or a status message, is passed in; the title and close button live here.
 */
export function PreviewPanel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <aside
      aria-label={title}
      className="fixed inset-0 z-50 flex flex-col gap-3 overflow-y-auto bg-background p-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1rem,env(safe-area-inset-bottom))] lg:static lg:inset-auto lg:z-auto lg:max-h-[calc(100vh-2rem)] lg:self-start lg:border lg:bg-card lg:sticky lg:top-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{title}</h2>
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
      {children}
    </aside>
  );
}
