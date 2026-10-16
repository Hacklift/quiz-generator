/**
 * Persona taxonomy — stable IDs and generation defaults with English fallback copy.
 *
 * The backend (server/app/users/persona.py) owns the same *slugs* but no copy;
 * server/tests/test_persona_taxonomy.py fails if the two drift. Adding or
 * renaming a slug means changing both files in the same PR.
 *
 * See PERSONA_SCAFFOLDING.md for which ticket owns which file.
 */

import personaMessages from "@features/locale/messages/persona.en.json";

export const PERSONA_CATEGORIES = ["school", "corporate"] as const;
export type PersonaCategory = (typeof PERSONA_CATEGORIES)[number];

export const SCHOOL_USER_TYPES = [
  "teacher",
  "lecturer",
  "student",
  "parent",
] as const;
export const CORPORATE_USER_TYPES = ["business", "employee", "hr"] as const;

export type SchoolUserType = (typeof SCHOOL_USER_TYPES)[number];
export type CorporateUserType = (typeof CORPORATE_USER_TYPES)[number];
export type PersonaUserType = SchoolUserType | CorporateUserType;

export const PERSONA_USER_TYPES: readonly PersonaUserType[] = [
  ...SCHOOL_USER_TYPES,
  ...CORPORATE_USER_TYPES,
];

export interface Persona {
  category: PersonaCategory;
  userType: PersonaUserType;
}

/** Seam for #133 (persona-aware generation defaults). */
export interface PersonaGenerationDefaults {
  audienceType: string;
  customInstruction: string;
  difficultyLevel: "easy" | "medium" | "hard";
  numQuestions: number;
  questionType: "multichoice" | "true-false" | "open-ended" | "short-answer";
}

export interface PersonaUserTypeDefinition {
  slug: PersonaUserType;
  category: PersonaCategory;
  label: string;
  description: string;
  defaultTopic: string;
  generationDefaults: PersonaGenerationDefaults;
}

export interface PersonaCategoryDefinition {
  slug: PersonaCategory;
  label: string;
  description: string;
  userTypes: PersonaUserTypeDefinition[];
}

/** Persona-aware generation defaults mapping for #133. */
export const PERSONA_TAXONOMY: Record<
  PersonaCategory,
  PersonaCategoryDefinition
> = {
  school: {
    slug: "school",
    label: personaMessages.categories.school.label,
    description: personaMessages.categories.school.description,
    userTypes: [
      {
        slug: "teacher",
        category: "school",
        label: personaMessages.roles.teacher.label,
        description: personaMessages.roles.teacher.description,
        defaultTopic: personaMessages.roles.teacher.defaultTopic,
        generationDefaults: {
          audienceType: "students",
          customInstruction:
            "Use clear classroom language, include marking-friendly questions, and keep the answer key suitable for teacher review.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "lecturer",
        category: "school",
        label: personaMessages.roles.lecturer.label,
        description: personaMessages.roles.lecturer.description,
        defaultTopic: personaMessages.roles.lecturer.defaultTopic,
        generationDefaults: {
          audienceType: "undergraduates",
          customInstruction:
            "Frame questions for lecture recap and seminar preparation, with concepts suitable for large cohorts.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "student",
        category: "school",
        label: personaMessages.roles.student.label,
        description: personaMessages.roles.student.description,
        defaultTopic: personaMessages.roles.student.defaultTopic,
        generationDefaults: {
          audienceType: "students",
          customInstruction:
            "Create self-practice questions with immediate learning value and wording suited to exam revision.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "parent",
        category: "school",
        label: personaMessages.roles.parent.label,
        description: personaMessages.roles.parent.description,
        defaultTopic: personaMessages.roles.parent.defaultTopic,
        generationDefaults: {
          audienceType: "children",
          customInstruction:
            "Use child-friendly wording, simple examples, and auto-marked questions a parent can review quickly.",
          difficultyLevel: "easy",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
    ],
  },
  corporate: {
    slug: "corporate",
    label: personaMessages.categories.corporate.label,
    description: personaMessages.categories.corporate.description,
    userTypes: [
      {
        slug: "business",
        category: "corporate",
        label: personaMessages.roles.business.label,
        description: personaMessages.roles.business.description,
        defaultTopic: personaMessages.roles.business.defaultTopic,
        generationDefaults: {
          audienceType: "employees",
          customInstruction:
            "Focus on onboarding and product-knowledge checks with practical workplace wording.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "employee",
        category: "corporate",
        label: personaMessages.roles.employee.label,
        description: personaMessages.roles.employee.description,
        defaultTopic: personaMessages.roles.employee.defaultTopic,
        generationDefaults: {
          audienceType: "employees",
          customInstruction:
            "Create self-paced upskilling questions with clear explanations and workplace examples.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "hr",
        category: "corporate",
        label: personaMessages.roles.hr.label,
        description: personaMessages.roles.hr.description,
        defaultTopic: personaMessages.roles.hr.defaultTopic,
        generationDefaults: {
          audienceType: "employees",
          customInstruction:
            "Use compliance-training wording, scenario-based checks, and clear pass/fail review language.",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
    ],
  },
};

const USER_TYPE_INDEX: Record<PersonaUserType, PersonaUserTypeDefinition> =
  Object.values(PERSONA_TAXONOMY).reduce(
    (index, category) => {
      for (const definition of category.userTypes) {
        index[definition.slug] = definition;
      }
      return index;
    },
    {} as Record<PersonaUserType, PersonaUserTypeDefinition>,
  );

/**
 * Labels shipped in production links before slugs existed
 * (e.g. /generate?persona=HR%20personnel). Keeps old bookmarks working.
 */
export const LEGACY_PERSONA_LABELS: Record<string, PersonaUserType> =
  Object.values(USER_TYPE_INDEX).reduce(
    (labels, definition) => {
      labels[definition.label.toLowerCase()] = definition.slug;
      return labels;
    },
    {} as Record<string, PersonaUserType>,
  );

export function isPersonaCategory(value: unknown): value is PersonaCategory {
  return (
    typeof value === "string" &&
    (PERSONA_CATEGORIES as readonly string[]).includes(value)
  );
}

export function isPersonaUserType(value: unknown): value is PersonaUserType {
  return (
    typeof value === "string" &&
    (PERSONA_USER_TYPES as readonly string[]).includes(value)
  );
}

export function getUserTypeDefinition(
  userType: PersonaUserType,
): PersonaUserTypeDefinition {
  return USER_TYPE_INDEX[userType];
}

export function getPersonaGenerationDefaults(
  userType: PersonaUserType,
): PersonaGenerationDefaults {
  return USER_TYPE_INDEX[userType].generationDefaults;
}

export function getCategoryDefinition(
  category: PersonaCategory,
): PersonaCategoryDefinition {
  return PERSONA_TAXONOMY[category];
}

export function categoryForUserType(
  userType: PersonaUserType,
): PersonaCategory {
  return USER_TYPE_INDEX[userType].category;
}

/**
 * Tolerant parser for persona values arriving from URLs, storage or the API.
 * Accepts slugs and legacy labels, infers the category from the user type, and
 * returns null when the pair is inconsistent or unrecognised.
 */
export function parsePersona(
  category?: string | null,
  userType?: string | null,
): Persona | null {
  const rawType = typeof userType === "string" ? userType.trim() : "";
  if (!rawType) return null;

  const normalized = rawType.toLowerCase();
  const slug: PersonaUserType | undefined = isPersonaUserType(normalized)
    ? normalized
    : LEGACY_PERSONA_LABELS[normalized];
  if (!slug) return null;

  const resolvedCategory = categoryForUserType(slug);
  const rawCategory =
    typeof category === "string" ? category.trim().toLowerCase() : "";

  // An explicit category that disagrees with the user type is a bad link.
  if (rawCategory && rawCategory !== resolvedCategory) return null;

  return { category: resolvedCategory, userType: slug };
}

/** The only place that builds a persona-carrying generate link. */
export function personaGenerateHref(userType: PersonaUserType): string {
  const definition = getUserTypeDefinition(userType);
  const params = new URLSearchParams({
    persona: definition.slug,
    category: definition.category,
  });
  return `/generate?${params.toString()}`;
}
