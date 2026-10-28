import { Moon, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";

/** Switches between the light and dark Polaris themes. */
export function ThemeToggle() {
  const { t } = useTranslation();
  const { theme, toggle } = useTheme();
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={theme === "dark" ? t("theme.switchToLight") : t("theme.switchToDark")}
    >
      {theme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}
