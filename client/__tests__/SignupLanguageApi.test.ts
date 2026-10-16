import { registerUser } from "@features/auth/api/authApi";
import { api } from "@shared/api/http";

jest.mock("@shared/api/http", () => ({
  api: { post: jest.fn() },
  API_BASE_URL: "http://localhost:8000",
}));
const payload = {
  username: "learner",
  email: "learner@example.com",
  full_name: "Learner Test",
  password: "ValidPass123!",
};
beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  (api.post as jest.Mock).mockResolvedValue({ data: {} });
});

test.each([null, "en", "fr"])(
  "explicit preference %s is not replaced by guest storage",
  async (preferred_locale) => {
    localStorage.setItem("quizwerk.guestLocale", "es");
    await registerUser({
      ...payload,
      preferred_locale,
      organization_invitation_token: "invitation",
    });
    expect(api.post).toHaveBeenCalledWith("/auth/register/", {
      ...payload,
      preferred_locale,
      organization_invitation_token: "invitation",
    });
  },
);

test("legacy callers can still preserve an explicit guest preference", async () => {
  localStorage.setItem("quizwerk.guestLocale", "fr");
  await registerUser(payload);
  expect(api.post).toHaveBeenCalledWith("/auth/register/", {
    ...payload,
    preferred_locale: "fr",
  });
});
