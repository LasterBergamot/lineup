import { useTranslation } from "react-i18next";
import { ComingSoon } from "@/pages/coming-soon";

export function SavedPage() {
  const { t } = useTranslation();
  return <ComingSoon title={t("pages.saved.title")} description={t("pages.saved.description")} />;
}
