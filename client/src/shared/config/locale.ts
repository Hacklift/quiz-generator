import languages from "@features/locale/languages.json";
export const FALLBACK_LOCALES = ["en", "es", "fr"] as const;
export type SupportedLocale = string;
export const DEFAULT_LOCALE = "en";
export const LANGUAGES = languages;
export const SUPPORTED_LOCALES = languages.map(({ code }) => code);
const codes = new Set(SUPPORTED_LOCALES);
export const LOCALE_DISPLAY_NAMES: Record<string, string> = {
  ...Object.fromEntries(languages.map(({ code, name }) => [code, name])),
  en: "English",
  es: "Español",
  fr: "Français",
};
export function isSupportedLocale(value: unknown): value is SupportedLocale {
  return typeof value === "string" && codes.has(value);
}
export function browserLocale(): SupportedLocale {
  return DEFAULT_LOCALE;
}
export function languageDirection(locale: string): "ltr" | "rtl" {
  try {
    const language = new Intl.Locale(locale) as Intl.Locale & {
      textInfo?: { direction: "ltr" | "rtl" };
      getTextInfo?: () => { direction: "ltr" | "rtl" };
    };
    return (
      language.getTextInfo?.().direction ??
      language.textInfo?.direction ??
      ([
        "ar",
        "he",
        "fa",
        "ur",
        "ps",
        "sd",
        "ug",
        "yi",
        "dv",
        "syr",
        "ckb",
      ].includes(locale)
        ? "rtl"
        : "ltr")
    );
  } catch {
    return "ltr";
  }
}
