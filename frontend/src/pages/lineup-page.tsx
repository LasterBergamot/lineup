import { useTranslation } from "react-i18next";
import { LineupForm } from "@/features/lineup/lineup-form";

/** One-off lineup: fill in the sheet and download it; nothing is stored. */
export function LineupPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("lineup.title")}</h1>
        <p className="text-muted-foreground">{t("lineup.description")}</p>
      </div>
      <LineupForm />
    </div>
  );
}
