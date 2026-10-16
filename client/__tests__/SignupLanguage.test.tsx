import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SignUpModal from "@features/auth/components/SignUpModal";
import { registerUser } from "@features/auth/api/authApi";
import { api } from "@shared/api/http";

const mockPreview = jest.fn();
const mockRouter = {
  query: {} as Record<string, string>,
  asPath: "/auth/register",
  isReady: true,
  push: jest.fn(),
};
jest.mock("next/router", () => ({ useRouter: () => mockRouter }));
jest.mock("@features/locale/context/localeContext", () => ({
  useLocale: () => ({ previewGuestLocale: mockPreview }),
}));
jest.mock("@features/auth/api/authApi", () => ({ registerUser: jest.fn() }));
jest.mock("@shared/api/http", () => ({ api: { post: jest.fn() } }));
jest.mock("@features/auth/components/VerifyEmailModal", () => ({
  __esModule: true,
  default: () => null,
}));

const open = () =>
  render(<SignUpModal isOpen onClose={jest.fn()} switchToSignIn={jest.fn()} />);
function submit(container: HTMLElement) {
  for (const [id, value] of Object.entries({
    username: "learner",
    name: "Learner Test",
    email: "learner@example.com",
    password: "ValidPass123!",
    confirmPassword: "ValidPass123!",
  })) {
    fireEvent.change(container.querySelector(`#${id}`)!, { target: { value } });
  }
  fireEvent.submit(container.querySelector("form")!);
}

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  window.history.replaceState({}, "", "/auth/register");
  mockRouter.query = {};
  mockRouter.isReady = true;
  (registerUser as jest.Mock).mockResolvedValue({});
  (api.post as jest.Mock).mockResolvedValue({
    data: {
      organization_id: "org",
      name: "French school",
      default_locale: "fr",
    },
  });
});

test("independent signup starts in English without requiring an organization", async () => {
  const { container } = open();
  expect(
    screen.getByRole("listbox", { name: "Preferred language" }),
  ).toHaveValue("en");
  expect(
    screen.queryByText("Use organization default"),
  ).not.toBeInTheDocument();
  submit(container);
  await waitFor(() =>
    expect(registerUser).toHaveBeenCalledWith(
      expect.objectContaining({
        preferred_locale: null,
        organization_invitation_token: undefined,
      }),
    ),
  );
  expect(api.post).not.toHaveBeenCalled();
});

test("signup language is searchable and explicit selection is submitted", async () => {
  const { container } = open();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "French" },
  });
  fireEvent.change(screen.getByRole("listbox"), { target: { value: "fr" } });
  expect(mockPreview).toHaveBeenLastCalledWith("fr");
  submit(container);
  await waitFor(() =>
    expect(registerUser).toHaveBeenCalledWith(
      expect.objectContaining({ preferred_locale: "fr" }),
    ),
  );
});

test("organization invitation defaults to inheritance even with a previous guest preference", async () => {
  localStorage.setItem("quizwerk.guestLocale", "es");
  window.history.replaceState(
    {},
    "",
    "/auth/register#organization_invite=signed-invitation",
  );
  const { container } = open();
  expect(await screen.findByText(/Joining French school/)).toBeInTheDocument();
  expect(screen.getByRole("listbox")).toHaveValue("inherit");
  expect(mockPreview).toHaveBeenLastCalledWith("fr");
  submit(container);
  await waitFor(() =>
    expect(registerUser).toHaveBeenCalledWith(
      expect.objectContaining({
        preferred_locale: null,
        organization_invitation_token: "signed-invitation",
      }),
    ),
  );
  expect(localStorage.getItem("quizwerk.guestLocale")).toBe("es");
});

test("an invitee can override the organization language with English", async () => {
  mockRouter.query = { organization_invite: "signed-invitation" };
  const { container } = open();
  await screen.findByText(/Joining French school/);
  fireEvent.change(screen.getByRole("listbox"), { target: { value: "en" } });
  submit(container);
  await waitFor(() =>
    expect(registerUser).toHaveBeenCalledWith(
      expect.objectContaining({
        preferred_locale: "en",
        organization_invitation_token: "signed-invitation",
      }),
    ),
  );
});

test("invalid invitations block signup rather than silently creating an independent account", async () => {
  mockRouter.query = { organization_invite: "invalid" };
  (api.post as jest.Mock).mockRejectedValueOnce(
    new Error("invalid invitation"),
  );
  const { container } = open();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "could not be verified",
  );
  expect(container.querySelector('button[type="submit"]')).toBeDisabled();
  submit(container);
  expect(registerUser).not.toHaveBeenCalled();
});

test("signup waits until Next has resolved invitation parameters", () => {
  mockRouter.isReady = false;
  const { container } = open();
  expect(container.querySelector('button[type="submit"]')).toBeDisabled();
  submit(container);
  expect(registerUser).not.toHaveBeenCalled();
});

test("closing signup cancels invitation loading and restores the guest language", async () => {
  localStorage.setItem("quizwerk.guestLocale", "es");
  mockRouter.query = { organization_invite: "signed-invitation" };
  let finish!: (value: unknown) => void;
  (api.post as jest.Mock).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const { unmount } = open();
  expect(screen.getByRole("listbox")).toBeDisabled();
  const signal = (api.post as jest.Mock).mock.calls[0][2].signal;
  unmount();
  expect(signal.aborted).toBe(true);
  expect(mockPreview).toHaveBeenLastCalledWith("es");
  finish({
    data: {
      organization_id: "org",
      name: "French school",
      default_locale: "fr",
    },
  });
  await Promise.resolve();
  expect(mockPreview).toHaveBeenLastCalledWith("es");
});
