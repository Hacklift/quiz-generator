import { resolvePersona } from "@features/persona/lib/resolvePersona";
import {
  readStoredPersona,
  readStoredPersonaTopic,
  writeStoredPersona,
} from "@features/persona/lib/personaStorage";
import {
  categoryForUserType,
  parsePersona,
  personaGenerateHref,
  PERSONA_USER_TYPES,
} from "@shared/config/persona";

const EMPTY_QUERY = { persona: null, category: null };

afterEach(() => {
  window.localStorage.clear();
});

describe("parsePersona", () => {
  test("accepts slugs", () => {
    expect(parsePersona("school", "teacher")).toEqual({
      category: "school",
      userType: "teacher",
    });
  });

  test("accepts legacy display labels from links already in the wild", () => {
    expect(parsePersona("corporate", "HR personnel")).toEqual({
      category: "corporate",
      userType: "hr",
    });
    expect(parsePersona(null, "Teacher")).toEqual({
      category: "school",
      userType: "teacher",
    });
  });

  test("infers the category when only a user type is given", () => {
    expect(parsePersona(null, "employee")?.category).toBe("corporate");
  });

  test("rejects a category that contradicts the user type", () => {
    expect(parsePersona("corporate", "teacher")).toBeNull();
  });

  test("rejects unknown and empty values", () => {
    expect(parsePersona("school", "principal")).toBeNull();
    expect(parsePersona("school", "")).toBeNull();
    expect(parsePersona(null, null)).toBeNull();
  });

  test("round-trips every user type through its generate link", () => {
    for (const userType of PERSONA_USER_TYPES) {
      const href = personaGenerateHref(userType);
      const params = new URLSearchParams(href.split("?")[1]);

      expect(parsePersona(params.get("category"), params.get("persona"))).toEqual({
        category: categoryForUserType(userType),
        userType,
      });
      expect(params.get("topic")).toBeTruthy();
    }
  });
});

describe("persona storage", () => {
  test("persists persona and its carried topic", () => {
    const persona = { category: "school" as const, userType: "teacher" as const };

    writeStoredPersona(persona, {
      topic: "Photosynthesis — Grade 8 biology",
    });

    expect(readStoredPersona()).toEqual(persona);
    expect(readStoredPersonaTopic(persona)).toBe(
      "Photosynthesis — Grade 8 biology",
    );
  });

  test("does not apply a stored topic to a different persona", () => {
    writeStoredPersona(
      { category: "school", userType: "teacher" },
      { topic: "Photosynthesis" },
    );

    expect(
      readStoredPersonaTopic({ category: "corporate", userType: "hr" }),
    ).toBeNull();
  });

  test("preserves topic when rewriting the same stored persona without topic", () => {
    const persona = { category: "school" as const, userType: "teacher" as const };

    writeStoredPersona(persona, { topic: "Photosynthesis" });
    writeStoredPersona(persona);

    expect(readStoredPersonaTopic(persona)).toBe("Photosynthesis");
  });

  test("clears old topic when storing a different persona without topic", () => {
    writeStoredPersona(
      { category: "school", userType: "teacher" },
      { topic: "Photosynthesis" },
    );

    const nextPersona = {
      category: "corporate" as const,
      userType: "hr" as const,
    };
    writeStoredPersona(nextPersona);

    expect(readStoredPersona()).toEqual(nextPersona);
    expect(readStoredPersonaTopic(nextPersona)).toBeNull();
  });
});

describe("resolvePersona precedence", () => {
  test("profile beats query and storage", () => {
    const result = resolvePersona({
      profile: { category: "corporate", userType: "hr" },
      query: { persona: "teacher", category: "school" },
      stored: { category: "school", userType: "student" },
    });

    expect(result).toEqual({
      persona: { category: "corporate", userType: "hr" },
      source: "profile",
    });
  });

  test("query beats storage when there is no profile persona", () => {
    const result = resolvePersona({
      profile: null,
      query: { persona: "lecturer", category: "school" },
      stored: { category: "school", userType: "student" },
    });

    expect(result.persona?.userType).toBe("lecturer");
    expect(result.source).toBe("query");
  });

  test("falls back to storage", () => {
    const result = resolvePersona({
      profile: { category: null, userType: null },
      query: EMPTY_QUERY,
      stored: { category: "corporate", userType: "employee" },
    });

    expect(result.persona?.userType).toBe("employee");
    expect(result.source).toBe("storage");
  });

  test("returns none when nothing is set", () => {
    expect(
      resolvePersona({ profile: null, query: EMPTY_QUERY, stored: null }),
    ).toEqual({ persona: null, source: "none" });
  });

  test("ignores an invalid profile persona and falls through", () => {
    const result = resolvePersona({
      profile: { category: "school", userType: "hr" },
      query: EMPTY_QUERY,
      stored: { category: "school", userType: "parent" },
    });

    expect(result.source).toBe("storage");
  });
});
