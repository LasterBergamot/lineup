import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";

/**
 * A button for an action that is hard to undo (removing a member, revoking a link). The first
 * click only asks "are you sure?" by swapping itself for a confirm and a cancel button, so a
 * stray tap on a phone cannot do it; there is no modal to trap focus in. `ariaLabel` tells screen
 * readers which row the button belongs to when the visible text is the same on every row.
 */
export function ConfirmButton({
  label,
  confirmLabel,
  ariaLabel,
  onConfirm,
  loading = false,
}: {
  label: string;
  confirmLabel: string;
  ariaLabel?: string;
  onConfirm: () => void;
  loading?: boolean;
}) {
  const { t } = useTranslation();
  const [asking, setAsking] = useState(false);
  if (!asking) {
    return (
      <Button size="sm" variant="outline" aria-label={ariaLabel} onClick={() => setAsking(true)}>
        {label}
      </Button>
    );
  }
  return (
    <span className="inline-flex gap-2">
      <Button size="sm" variant="destructive" loading={loading} onClick={onConfirm}>
        {confirmLabel}
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setAsking(false)}>
        {t("common.cancel")}
      </Button>
    </span>
  );
}
