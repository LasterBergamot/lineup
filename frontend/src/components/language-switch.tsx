import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { currentLanguage, setLanguage, SUPPORTED_LANGUAGES } from "@/i18n";
import { cn } from "@/lib/utils";

/**
 * Hungarian / English switch. Each button is named after its language in that language (so it
 * is readable whatever the UI currently says) and carries a matching `lang`, which makes screen
 * readers pronounce it correctly. The choice is remembered in localStorage by `setLanguage`.
 * A pill segmented control: the active language is the raised chip. It sits in the account panel
 * and on the sign-in page, so it works before signing in.
 */
export function LanguageSwitch({ className }: { className?: string }) {
  // Subscribing to the hook re-renders this component when the language changes.
  const { t } = useTranslation();
  const active = currentLanguage();
  return (
    <div
      role="group"
      aria-label={t("language.label")}
      className={cn("flex w-fit gap-0.5 rounded-pill bg-muted p-0.5", className)}
    >
      {SUPPORTED_LANGUAGES.map((language) => (
        <Button
          key={language}
          type="button"
          size="sm"
          variant="ghost"
          className={cn("rounded-pill", language === active && "bg-card shadow-xs hover:bg-card")}
          lang={language}
          aria-label={t(`language.${language}`)}
          aria-pressed={language === active}
          onClick={() => void setLanguage(language)}
        >
          <span aria-hidden="true">{language.toUpperCase()}</span>
        </Button>
      ))}
    </div>
  );
}
