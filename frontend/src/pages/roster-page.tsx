import { useTranslation } from "react-i18next";
import { DirectoryCard } from "@/features/directory/directory-card";
import { PlayersCard } from "@/features/players/players-card";
import { useTeams } from "@/features/teams/context";
import { TeamSettingsCard } from "@/features/teams/team-settings-card";

/**
 * The current team's roster: its players (everyone in the team can edit them), the team settings
 * (owners only) and a search over the shared opponent directory. The settings card is hidden from
 * members as a courtesy; the server answers 403 to them regardless.
 */
export function RosterPage() {
  const { t } = useTranslation();
  const { current } = useTeams();
  if (!current) return null;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("pages.roster.title")}</h1>
        <p className="text-muted-foreground">
          {t("pages.roster.description", { team: current.name })}
        </p>
      </div>
      <div className="grid max-w-3xl gap-6">
        <PlayersCard team={current} />
        {current.role === "owner" && <TeamSettingsCard team={current} />}
        <DirectoryCard />
      </div>
    </div>
  );
}
