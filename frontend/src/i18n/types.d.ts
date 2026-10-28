import type hu from "@/i18n/locales/hu.json";

// Makes `t("…")` keys type-checked against the Hungarian bundle (the English one must have the
// same keys; a test enforces it), so a typo in a key fails `tsc` instead of showing the key.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: { translation: typeof hu };
  }
}
