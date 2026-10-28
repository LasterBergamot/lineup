import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "@/i18n/locales/en.json";
import hu from "@/i18n/locales/hu.json";

export const SUPPORTED_LANGUAGES = ["hu", "en"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

/** Hungarian is the default: the clubs, the users and the generated document are Hungarian. */
export const DEFAULT_LANGUAGE: Language = "hu";

/**
 * The one localStorage entry this feature owns. The visitor's language choice is a strictly
 * necessary UI preference (like `lineup-theme`): nothing else about them is stored, and nothing
 * is written until they pick a language themselves.
 */
export const LANGUAGE_STORAGE_KEY = "lineup-lang";

/** Keeps `<html lang>` in step with the UI language (screen readers, hyphenation, spell check). */
function syncHtmlLang(language: string | undefined): void {
  document.documentElement.lang = language ?? DEFAULT_LANGUAGE;
}

/**
 * The app's i18next instance. Both locale bundles ship in the main chunk (two small files, so
 * no HTTP backend: no extra request, nothing to leak). The only language source is the
 * `lineup-lang` entry in localStorage, never the browser's `Accept-Language`, so a first visit
 * is always Hungarian. The detector does not write by itself (`caches: []`): {@link setLanguage}
 * stores the choice, so merely rendering the app leaves storage untouched.
 */
export const i18n = i18next;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { hu: { translation: hu }, en: { translation: en } },
    supportedLngs: SUPPORTED_LANGUAGES,
    fallbackLng: DEFAULT_LANGUAGE,
    detection: { order: ["localStorage"], lookupLocalStorage: LANGUAGE_STORAGE_KEY, caches: [] },
    // React escapes output already.
    interpolation: { escapeValue: false },
    // The resources are bundled, so initialisation is synchronous and there is no loading state.
    initAsync: false,
  });

syncHtmlLang(i18n.resolvedLanguage);
i18n.on("languageChanged", () => syncHtmlLang(i18n.resolvedLanguage));

/** The language currently shown, always one of {@link SUPPORTED_LANGUAGES}. */
export function currentLanguage(): Language {
  return i18n.resolvedLanguage === "en" ? "en" : DEFAULT_LANGUAGE;
}

/**
 * Switches the UI language and remembers it in localStorage. Storage can be blocked (private
 * mode, strict settings); the switch still applies for this page view then.
 */
export async function setLanguage(language: Language): Promise<void> {
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // Not remembered; the language still changes below.
  }
  await i18n.changeLanguage(language);
}
