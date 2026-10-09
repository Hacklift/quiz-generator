import { createInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import { DEFAULT_LOCALE } from "@shared/config/locale";
import en from "./messages/en.json";
import es from "./messages/es.json";
import fr from "./messages/fr.json";
import personaEn from "./messages/persona.en.json";
import personaEs from "./messages/persona.es.json";
import personaFr from "./messages/persona.fr.json";

export function createLocaleI18n() {
  const instance = createInstance();
  void instance.init({
    resources: {
      en: { translation: en, persona: personaEn },
      es: { translation: es, persona: personaEs },
      fr: { translation: fr, persona: personaFr },
    },
    lng: DEFAULT_LOCALE,
    fallbackLng: DEFAULT_LOCALE,
    defaultNS: "translation",
    initAsync: false,
    interpolation: { escapeValue: false },
  });
  return instance;
}

// Standalone components have a deterministic English fallback. App renders get
// their own instance, preventing one user's language from affecting another.
const i18n = createLocaleI18n();
initReactI18next.init(i18n);
export default i18n;
