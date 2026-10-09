/**
 * Locale-aware terminology, resolved as role override → category → neutral.
 * The optional locale preserves the English API for non-React callers.
 */
import type { Persona, PersonaCategory, PersonaUserType } from "./persona";
import type { SupportedLocale } from "./locale";
import en from "@features/locale/messages/persona.en.json";
import es from "@features/locale/messages/persona.es.json";
import fr from "@features/locale/messages/persona.fr.json";

export type TermKey =
  | "learner"
  | "group"
  | "quiz"
  | "live_quiz"
  | "assignment"
  | "library"
  | "report"
  | "session";
export type TermForm = "singular" | "plural";
export type TerminologyResolver = (key: TermKey, form?: TermForm) => string;
export interface TermDefinition {
  singular: string;
  plural: string;
}
export type TerminologyMap = Partial<Record<TermKey, TermDefinition>>;
interface TermCatalog {
  defaultTerms: Record<TermKey, TermDefinition>;
  categoryTerms: Record<PersonaCategory, TerminologyMap>;
  userTypeTerms: Partial<Record<PersonaUserType, TerminologyMap>>;
}
const catalogs: Record<SupportedLocale, TermCatalog> = {
  en: en.terms,
  es: es.terms,
  fr: fr.terms,
};
export const DEFAULT_TERMS = catalogs.en.defaultTerms;
export const CATEGORY_TERMS = catalogs.en.categoryTerms;
export const USER_TYPE_TERMS = catalogs.en.userTypeTerms;

/** Stable message key; useTerms translates it with the current i18n instance. */
export function termMessageKey(
  key: TermKey,
  persona: Persona | null,
  form: TermForm = "singular",
): string {
  if (persona && USER_TYPE_TERMS[persona.userType]?.[key]) {
    return `terms.userTypeTerms.${persona.userType}.${key}.${form}`;
  }
  if (persona && CATEGORY_TERMS[persona.category]?.[key]) {
    return `terms.categoryTerms.${persona.category}.${key}.${form}`;
  }
  return `terms.defaultTerms.${key}.${form}`;
}

export function resolveTerm(
  key: TermKey,
  persona: Persona | null,
  form: TermForm = "singular",
  locale: SupportedLocale = "en",
): string {
  const catalog = catalogs[locale];
  const definition =
    (persona && catalog.userTypeTerms[persona.userType]?.[key]) ||
    (persona && catalog.categoryTerms[persona.category]?.[key]) ||
    catalog.defaultTerms[key];
  return definition[form];
}

export function titleCaseTerm(term: string): string {
  return term.charAt(0).toUpperCase() + term.slice(1);
}
