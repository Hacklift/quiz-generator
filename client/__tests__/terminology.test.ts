import { resolveTerm } from "@shared/config/terminology";

describe("resolveTerm", () => {
  test("falls back to neutral wording when persona is unset", () => {
    expect(resolveTerm("learner", null, "plural")).toBe("learners");
    expect(resolveTerm("group", null)).toBe("group");
  });

  test("uses category wording", () => {
    const teacher = { category: "school", userType: "teacher" } as const;
    const business = { category: "corporate", userType: "business" } as const;

    expect(resolveTerm("learner", teacher, "plural")).toBe("students");
    expect(resolveTerm("group", teacher)).toBe("class");
    expect(resolveTerm("learner", business, "plural")).toBe("employees");
    expect(resolveTerm("group", business)).toBe("team");
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
