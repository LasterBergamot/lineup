import { useTranslation } from "react-i18next";
import { ComingSoon } from "@/pages/coming-soon";

export function RosterPage() {
  const { t } = useTranslation();
  return <ComingSoon title={t("pages.roster.title")} description={t("pages.roster.description")} />;
}
