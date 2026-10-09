import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useTranslation } from "react-i18next";
import {
  LocaleProvider,
  useLocale,
} from "@features/locale/context/localeContext";
import type { User } from "@features/auth/types/User";

const mockUpdateLocale = jest.fn();
const mockRefreshUser = jest.fn();
let mockUser: User | null;
jest.mock("@features/auth/api/authApi", () => ({
  updateLocale: (...args: unknown[]) => mockUpdateLocale(...args),
}));
jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ user: mockUser, refreshUser: mockRefreshUser }),
}));

function Probe() {
  const { locale, setPreferredLocale } = useLocale();
  const { t } = useTranslation();
  const [error, setError] = React.useState(false);
  return (
    <>
      <p>
        {locale}|{t("language.settings")}
      </p>
      <button
        onClick={() =>
          void setPreferredLocale("fr").catch(() => setError(true))
        }
      >
        French
      </button>
      <button
        onClick={() =>
          void setPreferredLocale(null).catch(() => setError(true))
        }
      >
        Inherit
      </button>
      {error && <p role="alert">Save failed</p>}
    </>
  );
}
const app = () => (
  <LocaleProvider>
    <Probe />
  </LocaleProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
  mockUser = {
    id: "a",
    username: "learner",
    email: "learner@example.com",
    is_verified: true,
    preferred_locale: "es",
    effective_locale: "es",
  };
  mockUpdateLocale.mockResolvedValue({});
  mockRefreshUser.mockResolvedValue(undefined);
});

test("failed writes preserve the current language and document metadata", async () => {
  mockUpdateLocale.mockRejectedValueOnce(new Error("offline"));
  render(app());
  expect(await screen.findByText("es|Idioma")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "French" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByText("es|Idioma")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("es");
  expect(mockRefreshUser).not.toHaveBeenCalled();
});

test("clearing the preference uses the refreshed organization default", async () => {
  const { rerender } = render(app());
  fireEvent.click(screen.getByRole("button", { name: "Inherit" }));
  await waitFor(() => expect(mockRefreshUser).toHaveBeenCalled());
  expect(mockUpdateLocale).toHaveBeenCalledWith({ preferred_locale: null });
  mockUser = { ...mockUser!, preferred_locale: null, effective_locale: "fr" };
  rerender(app());
  expect(await screen.findByText("fr|Langue")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("fr");
});

test("switching accounts applies the new profile locale", async () => {
  const { rerender } = render(app());
  expect(await screen.findByText("es|Idioma")).toBeInTheDocument();
  mockUser = {
    ...mockUser!,
    id: "b",
    preferred_locale: null,
    effective_locale: "en",
  };
  rerender(app());
  expect(await screen.findByText("en|Language")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("en");
});
