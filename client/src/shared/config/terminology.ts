/**
 * Category-aware terminology.
 *
 * A School user should read "students" and "class" where a Corporate user
 * reads "employees" and "team". Persona views must never hardcode those
 * nouns — call `t(...)` from `useTerms()` instead.
 *
 * Resolution order: user-type override -> category -> neutral default, so an
 * unset persona always produces a sensible string.
 *
 * Adding a term: add the key to `TermKey`, a neutral entry to DEFAULT_TERMS,
 * then only the category/user-type entries that actually differ.
 */
import type { Persona, PersonaCategory, PersonaUserType } from "./persona";

export type TermKey =
  | "learner"
  | "group"
  | "assignment"
  | "library"
  | "report"
  | "session";

export interface TermDefinition {
  singular: string;
  plural: string;
}

export type TerminologyMap = Partial<Record<TermKey, TermDefinition>>;

export const DEFAULT_TERMS: Record<TermKey, TermDefinition> = {
  learner: { singular: "learner", plural: "learners" },
  group: { singular: "group", plural: "groups" },
  assignment: { singular: "quiz", plural: "quizzes" },
  library: { singular: "library", plural: "libraries" },
  report: { singular: "report", plural: "reports" },
  session: { singular: "session", plural: "sessions" },
};

export const CATEGORY_TERMS: Record<PersonaCategory, TerminologyMap> = {
  school: {
    learner: { singular: "student", plural: "students" },
    group: { singular: "class", plural: "classes" },
    assignment: { singular: "homework", plural: "homework" },
    library: { singular: "resources", plural: "resources" },
    report: { singular: "gradebook", plural: "gradebooks" },
    session: { singular: "lesson", plural: "lessons" },
  },
  corporate: {
    learner: { singular: "employee", plural: "employees" },
    group: { singular: "team", plural: "teams" },
    assignment: { singular: "course", plural: "courses" },
    library: { singular: "training catalogue", plural: "training catalogues" },
    report: { singular: "compliance record", plural: "compliance records" },
    session: { singular: "training session", plural: "training sessions" },
  },
};

/**
 * Overrides for a single user type, where the category default is wrong.
 * Kept deliberately sparse — most user types inherit their category.
 */
export const USER_TYPE_TERMS: Partial<
  Record<PersonaUserType, TerminologyMap>
> = {
  lecturer: {
    group: { singular: "cohort", plural: "cohorts" },
    session: { singular: "lecture", plural: "lectures" },
  },
  parent: {
    learner: { singular: "child", plural: "children" },
    assignment: { singular: "practice set", plural: "practice sets" },
  },
  hr: {
    assignment: { singular: "compliance course", plural: "compliance courses" },
  },
};

export function resolveTerm(
  key: TermKey,
  persona: Persona | null,
  form: "singular" | "plural" = "singular",
): string {
  const fromUserType = persona
    ? USER_TYPE_TERMS[persona.userType]?.[key]
    : undefined;
  const fromCategory = persona ? CATEGORY_TERMS[persona.category]?.[key] : undefined;

  const definition = fromUserType ?? fromCategory ?? DEFAULT_TERMS[key];
  return definition[form];
}

/** Capitalises the first letter — for headings and sentence starts. */
export function titleCaseTerm(term: string): string {
  return term.charAt(0).toUpperCase() + term.slice(1);
}
