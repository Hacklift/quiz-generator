import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import SignInModal from "../components/auth/SignInModal";

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({ login: jest.fn() }),
}));

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

describe("SignInModal", () => {
  const mockOnClose = jest.fn();
  const mockSwitchToSignUp = jest.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  test("renders the modal when isOpen is true", () => {
    render(
      <SignInModal
        isOpen
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
        isOpen
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
});
