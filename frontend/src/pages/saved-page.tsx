import { useTranslation } from "react-i18next";
import { SavedLineups } from "@/features/saved/saved-lineups";
import { useTeams } from "@/features/teams/context";

/**
 * The current team's saved lineups: browse them newest first, preview the PDF, download it again,
 * clone one into a new lineup or delete it. Every member of the team sees and manages the same list.
 */
export function SavedPage() {
  const { t } = useTranslation();
  const { current } = useTeams();
  if (!current) return null;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("pages.saved.title")}</h1>
        <p className="text-muted-foreground">{t("pages.saved.description")}</p>
      </div>
      <SavedLineups team={current} />
    </div>
  );
}
