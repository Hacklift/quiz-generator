import {
  getPresetsForLevel,
  PARENT_PRACTICE_PRESETS,
  resolveParentPracticePreset,
} from "@features/parent-practice/config/presets";

describe("Parent Practice presets", () => {
  test("preset identifiers are unique", () => {
    const ids = PARENT_PRACTICE_PRESETS.map((preset) => preset.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("only exposes presets appropriate for a level", () => {
    expect(getPresetsForLevel("ages-5-7").map((preset) => preset.id)).toEqual([
      "addition-subtraction",
      "vocabulary-practice",
    ]);
    expect(getPresetsForLevel("ages-9-11").map((preset) => preset.id)).toEqual([
      "multiplication-tables",
      "basic-fractions",
      "vocabulary-practice",
    ]);
  });

  test("resolves multiplication practice into the existing QuizRequest fields", () => {
    expect(
      resolveParentPracticePreset("ages-7-9", "multiplication-tables"),
    ).toEqual(
      expect.objectContaining({
        profession: "Multiplication tables from 2 to 10 — ages 7 to 9",
        audience_type: "children ages 7–9",
        difficulty_level: "easy",
        question_type: "multichoice",
        num_questions: 10,
      }),
    );
  });

  test("allows a valid question-count override", () => {
    expect(
      resolveParentPracticePreset(
        "ages-9-11",
        "basic-fractions",
        6,
      ).num_questions,
    ).toBe(6);
  });

  test("rejects a preset that is unavailable for the selected level", () => {
    expect(() =>
      resolveParentPracticePreset("ages-5-7", "basic-fractions"),
    ).toThrow(/not available/i);
  });
});
