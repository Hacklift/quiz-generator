import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SignInModal from "@features/auth/components/SignInModal";
import { login } from "@features/auth/api/authApi";

const mockRouterPush = jest.fn();
const mockAuthLogin = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({
    push: mockRouterPush,
  }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    login: mockAuthLogin,
  }),
}));

jest.mock("@features/auth/api/authApi", () => ({
  login: jest.fn().mockResolvedValue({
    access_token: "test-access-token",
    token_type: "bearer",
  }),
}));

const mockLogin = login as jest.Mock;

describe("SignInModal", () => {
  const mockOnClose = jest.fn();
  const mockSwitchToSignUp = jest.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockSwitchToSignUp.mockClear();
    mockRouterPush.mockClear();
    mockAuthLogin.mockClear();
    mockLogin.mockReset();
    mockLogin.mockResolvedValue({
      access_token: "test-access-token",
      token_type: "bearer",
    });
  });

  test("renders the modal when isOpen is true", () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /sign in/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("email@example.com or username"),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Enter your password"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  test("does not render the modal when isOpen is false", () => {
    render(
      <SignInModal
        isOpen={false}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    expect(
      screen.queryByRole("heading", { name: /sign in/i }),
    ).not.toBeInTheDocument();
  });

  test("updates input fields on change", () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    const usernameInput = screen.getByPlaceholderText(
      "email@example.com or username",
    );
    const passwordInput = screen.getByPlaceholderText("Enter your password");

    fireEvent.change(usernameInput, {
      target: { value: "testuser@example.com" },
    });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    expect(usernameInput).toHaveValue("testuser@example.com");
    expect(passwordInput).toHaveValue("password123");
  });

  test("calls onClose when form is submitted", async () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    const usernameInput = screen.getByPlaceholderText(
      "email@example.com or username",
    );
    const passwordInput = screen.getByPlaceholderText("Enter your password");
    const signInButton = screen.getByRole("button", { name: /sign in/i });

    fireEvent.change(usernameInput, {
      target: { value: "testuser@example.com" },
    });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    fireEvent.click(signInButton);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  test("calls onClose when close button is clicked", () => {
    const { container } = render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    fireEvent.click(container.firstChild as Element);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test("shows a concrete login error when the request fails", async () => {
    mockLogin.mockRejectedValue(new Error("Account is not active"));

    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={mockSwitchToSignUp}
      />,
    );

    fireEvent.change(
      screen.getByPlaceholderText("email@example.com or username"),
      {
        target: { value: "blocked-user@example.com" },
      },
    );
    fireEvent.change(screen.getByPlaceholderText("Enter your password"), {
      target: { value: "password123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(
      await screen.findByText("Account is not active"),
    ).toBeInTheDocument();
    expect(mockOnClose).not.toHaveBeenCalled();
  });
});
