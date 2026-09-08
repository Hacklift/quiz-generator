import { navigationItems } from "@features/quiz/components/NavBar";

describe("navigationItems", () => {
  test("keeps quiz creation as the dedicated navigation CTA", () => {
    const items = navigationItems();

    expect(items).not.toContainEqual(
      expect.objectContaining({ href: "/generate" }),
    );
  });
});
