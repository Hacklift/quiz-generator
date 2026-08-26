/**
 * Persona taxonomy — the single source of truth for persona copy on the client.
 *
 * The backend (server/app/users/persona.py) owns the same *slugs* but no copy;
 * server/tests/test_persona_taxonomy.py fails if the two drift. Adding or
 * renaming a slug means changing both files in the same PR.
 *
 * See PERSONA_SCAFFOLDING.md for which ticket owns which file.
 */

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
    label: "School",
    description: "Teachers, lecturers, students and parents.",
    userTypes: [
      {
        slug: "teacher",
        category: "school",
        label: "Teacher",
        description: "Class quizzes, homework checks, exam revision",
        defaultTopic: "Photosynthesis — Grade 8 biology",
        generationDefaults: {
          audienceType: "students",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "lecturer",
        category: "school",
        label: "Lecturer",
        description: "Lecture recaps and seminar prep for large cohorts",
        defaultTopic: "Introduction to microeconomics",
        generationDefaults: {
          audienceType: "undergraduates",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "student",
        category: "school",
        label: "Student",
        description: "Self-testing before the exam",
        defaultTopic: "World War II — key dates and causes",
        generationDefaults: {
          audienceType: "students",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "parent",
        category: "school",
        label: "Parent",
        description: "Practice at home, marked automatically",
        defaultTopic: "Multiplication tables — ages 7 to 9",
        generationDefaults: {
          audienceType: "children",
          difficultyLevel: "easy",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
    ],
  },
  corporate: {
    slug: "corporate",
    label: "Corporate",
    description: "Businesses, employees and HR personnel.",
    userTypes: [
      {
        slug: "business",
        category: "corporate",
        label: "Business",
        description: "Onboarding and product knowledge at scale",
        defaultTopic: "Company onboarding essentials",
        generationDefaults: {
          audienceType: "employees",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "employee",
        category: "corporate",
        label: "Employee",
        description: "Upskill and certify at your own pace",
        defaultTopic: "Data protection basics",
        generationDefaults: {
          audienceType: "employees",
          difficultyLevel: "medium",
          numQuestions: 10,
          questionType: "multichoice",
        },
      },
      {
        slug: "hr",
        category: "corporate",
        label: "HR personnel",
        description: "Compliance training with an audit trail",
        defaultTopic: "Workplace policy — harassment prevention",
        generationDefaults: {
          audienceType: "employees",
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
    topic: definition.defaultTopic,
  });
  return `/generate?${params.toString()}`;
}
