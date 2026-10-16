import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import LanguageOnboarding from "@features/locale/components/LanguageOnboarding";

const mockSave = jest.fn();
let mockUser: {
  id: string;
  onboarding_organization_id?: string;
  language_selected?: boolean;
  preferred_locale?: string;
};
let mockLocale = "en";
jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ user: mockUser, isLoading: false }),
}));
jest.mock("@features/locale/context/localeContext", () => ({
  useLocale: () => ({
    locale: mockLocale,
    preferredLocale: null,
    setPreferredLocale: mockSave,
  }),
}));

beforeEach(() => {
  jest.clearAllMocks();
  mockSave.mockResolvedValue(undefined);
  mockUser = { id: "learner" };
  mockLocale = "en";
});

test("independent users can confirm English", async () => {
  render(<LanguageOnboarding />);
  expect(screen.getByRole("listbox")).toHaveValue("en");
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  await waitFor(() => expect(mockSave).toHaveBeenCalledWith("en"));
});

test("organization invitees can keep their inherited language", async () => {
  mockUser.onboarding_organization_id = "org";
  mockLocale = "fr";
  render(<LanguageOnboarding />);
  expect(screen.getByRole("listbox")).toHaveValue("inherit");
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  await waitFor(() => expect(mockSave).toHaveBeenCalledWith(null));
});

test("an invitee can change language and review it before Continue", async () => {
  mockUser.onboarding_organization_id = "org";
  mockLocale = "fr";
  render(<LanguageOnboarding />);
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "Spanish" },
  });
  fireEvent.change(screen.getByRole("listbox"), { target: { value: "es" } });
  expect(screen.getByRole("listbox")).toHaveValue("es");
  expect(mockSave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  await waitFor(() => expect(mockSave).toHaveBeenCalledWith("es"));
});

test("an explicit signup choice does not trigger a redundant onboarding prompt", () => {
  mockUser.preferred_locale = "es";
  mockUser.language_selected = true;
  render(<LanguageOnboarding />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("failed saves leave the selection available for retry", async () => {
  mockSave.mockRejectedValueOnce(new Error("offline"));
  render(<LanguageOnboarding />);
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "French" },
  });
  fireEvent.change(screen.getByRole("listbox"), { target: { value: "fr" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByRole("listbox")).toHaveValue("fr");
});
