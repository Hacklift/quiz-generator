import { resolveTerm } from "@shared/config/terminology";

describe("resolveTerm", () => {
  test("falls back to neutral wording when persona is unset", () => {
    expect(resolveTerm("learner", null, "plural")).toBe("learners");
    expect(resolveTerm("group", null)).toBe("group");
    expect(resolveTerm("quiz", null)).toBe("quiz");
    expect(resolveTerm("live_quiz", null)).toBe("live quiz");
    expect(resolveTerm("session", null)).toBe("session");
  });

  test("uses category wording", () => {
    const teacher = { category: "school", userType: "teacher" } as const;
    const business = { category: "corporate", userType: "business" } as const;

    expect(resolveTerm("learner", teacher, "plural")).toBe("students");
    expect(resolveTerm("group", teacher)).toBe("class");
    expect(resolveTerm("quiz", teacher)).toBe("class quiz");
    expect(resolveTerm("live_quiz", teacher)).toBe("live class quiz");
    expect(resolveTerm("session", teacher)).toBe("class quiz");
    expect(resolveTerm("learner", business, "plural")).toBe("team members");
    expect(resolveTerm("group", business)).toBe("team");
    expect(resolveTerm("quiz", business)).toBe("training quiz");
    expect(resolveTerm("live_quiz", business)).toBe("live training session");
    expect(resolveTerm("session", business)).toBe("training session");
  });

  test("user-type overrides beat the category", () => {
    const lecturer = { category: "school", userType: "lecturer" } as const;
    const parent = { category: "school", userType: "parent" } as const;

    expect(resolveTerm("group", lecturer)).toBe("cohort");
    expect(resolveTerm("learner", parent, "plural")).toBe("children");
  });

  test("a user type without an override inherits its category", () => {
    const lecturer = { category: "school", userType: "lecturer" } as const;

    // lecturer overrides group/session but not learner
    expect(resolveTerm("learner", lecturer, "plural")).toBe("students");
    expect(resolveTerm("live_quiz", lecturer)).toBe("live class quiz");
  });

  test("reports differ per category", () => {
    expect(
      resolveTerm("report", { category: "school", userType: "teacher" }),
    ).toBe("gradebook");
    expect(
      resolveTerm("report", { category: "corporate", userType: "hr" }),
    ).toBe("compliance record");
  });
});
