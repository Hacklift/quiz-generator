export const PARENT_PRACTICE_LEVELS = [
  { id: "ages-5-7", label: "Ages 5–7" },
  { id: "ages-7-9", label: "Ages 7–9" },
  { id: "ages-9-11", label: "Ages 9–11" },
] as const;

export type ParentPracticeLevel =
  (typeof PARENT_PRACTICE_LEVELS)[number]["id"];

export type ParentPracticePresetId =
  | "addition-subtraction"
  | "multiplication-tables"
  | "basic-fractions"
  | "vocabulary-practice";

export interface ParentPracticeGenerationParams {
  profession: string;
  audience_type: string;
  difficulty_level: "easy" | "medium";
  question_type: "multichoice";
  num_questions: number;
  custom_instruction: string;
}

export interface ParentPracticePreset {
  id: ParentPracticePresetId;
  label: string;
  levels: readonly ParentPracticeLevel[];
  topic: Record<ParentPracticeLevel, string | undefined>;
  instruction: string;
}

export const PARENT_PRACTICE_PRESETS: readonly ParentPracticePreset[] = [
  {
    id: "addition-subtraction",
    label: "Addition & Subtraction",
    levels: ["ages-5-7", "ages-7-9"],
    topic: {
      "ages-5-7": "Addition and subtraction within 20 — ages 5 to 7",
      "ages-7-9": "Addition and subtraction within 1,000 — ages 7 to 9",
      "ages-9-11": undefined,
    },
    instruction:
      "Use clear whole-number calculations and exactly one unambiguous correct option.",
  },
  {
    id: "multiplication-tables",
    label: "Multiplication Tables",
    levels: ["ages-7-9", "ages-9-11"],
    topic: {
      "ages-5-7": undefined,
      "ages-7-9": "Multiplication tables from 2 to 10 — ages 7 to 9",
      "ages-9-11": "Multiplication and division facts up to 12 × 12 — ages 9 to 11",
    },
    instruction:
      "Use exact multiplication or related division facts and exactly one unambiguous correct option.",
  },
  {
    id: "basic-fractions",
    label: "Basic Fractions",
    levels: ["ages-9-11"],
    topic: {
      "ages-5-7": undefined,
      "ages-7-9": undefined,
      "ages-9-11": "Basic fractions and equivalent fractions — ages 9 to 11",
    },
    instruction:
      "Use age-appropriate fraction recognition and equivalence with exactly one unambiguous correct option.",
  },
  {
    id: "vocabulary-practice",
    label: "Vocabulary Practice",
    levels: ["ages-5-7", "ages-7-9", "ages-9-11"],
    topic: {
      "ages-5-7": "Everyday vocabulary and word meanings — ages 5 to 7",
      "ages-7-9": "Vocabulary, synonyms and word meanings — ages 7 to 9",
      "ages-9-11": "Vocabulary, synonyms, antonyms and context — ages 9 to 11",
    },
    instruction:
      "Use child-friendly vocabulary in context and exactly one unambiguous correct option.",
  },
] as const;

export function getPresetsForLevel(level: ParentPracticeLevel) {
  return PARENT_PRACTICE_PRESETS.filter((preset) =>
    preset.levels.includes(level),
  );
}

export function resolveParentPracticePreset(
  level: ParentPracticeLevel,
  presetId: ParentPracticePresetId,
  numQuestions = 10,
): ParentPracticeGenerationParams {
  const preset = PARENT_PRACTICE_PRESETS.find(
    (candidate) => candidate.id === presetId,
  );
  const topic = preset?.topic[level];
  if (!preset || !preset.levels.includes(level) || !topic) {
    throw new Error("This practice preset is not available for the selected level.");
  }
  if (!Number.isInteger(numQuestions) || numQuestions < 1) {
    throw new Error("Number of questions must be a positive whole number.");
  }

  const levelLabel = PARENT_PRACTICE_LEVELS.find(
    (candidate) => candidate.id === level,
  )?.label;
  return {
    profession: topic,
    audience_type: `children ${levelLabel?.toLowerCase()}`,
    difficulty_level: level === "ages-9-11" ? "medium" : "easy",
    question_type: "multichoice",
    num_questions: numQuestions,
    custom_instruction: `${preset.instruction} Keep all content appropriate for ${levelLabel}.`,
  };
}
