import { EMAIL_REGEX, PASSWORD_REGEX } from "../constants/patterns/patterns";

describe("patterns", () => {
  test("EMAIL_REGEX matches valid emails", () => {
    expect(EMAIL_REGEX.test("user@example.com")).toBe(true);
    expect(EMAIL_REGEX.test("user.name+tag@domain.co")).toBe(true);
  });

  test("EMAIL_REGEX rejects invalid emails", () => {
    expect(EMAIL_REGEX.test("user@")).toBe(false);
    expect(EMAIL_REGEX.test("user@domain")).toBe(false);
    expect(EMAIL_REGEX.test("userdomain.com")).toBe(false);
  });

  test("PASSWORD_REGEX matches valid passwords", () => {
    expect(PASSWORD_REGEX.test("Abcd1234!")).toBe(true);
  });

  test("PASSWORD_REGEX rejects invalid passwords", () => {
    expect(PASSWORD_REGEX.test("abcd1234!")).toBe(false);
    expect(PASSWORD_REGEX.test("ABCD1234!")).toBe(false);
    expect(PASSWORD_REGEX.test("Abcdabcd!")).toBe(false);
    expect(PASSWORD_REGEX.test("Abcd1234")).toBe(false);
    expect(PASSWORD_REGEX.test("Ab1!")).toBe(false);
  });
});
