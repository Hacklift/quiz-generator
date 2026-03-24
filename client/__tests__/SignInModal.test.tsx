import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SignInModal from "../components/auth/SignInModal";

const push = jest.fn();
const authLogin = jest.fn();
const mockLogin = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({ login: authLogin }),
}));

jest.mock("../lib", () => ({
  login: (...args: unknown[]) => mockLogin(...args),
}));

describe("SignInModal", () => {
  const mockOnClose = jest.fn();
  const switchToSignUp = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders the modal when open", () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={switchToSignUp}
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
      screen.getByRole("button", { name: /^sign in$/i }),
    ).toBeInTheDocument();
  });

  test("does not render the modal when closed", () => {
    render(
      <SignInModal
        isOpen={false}
        onClose={mockOnClose}
        switchToSignUp={switchToSignUp}
      />,
    );

    expect(
      screen.queryByRole("heading", { name: /sign in/i }),
    ).not.toBeInTheDocument();
  });

  test("updates form fields on change", () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={switchToSignUp}
      />,
    );

    const identifierInput = screen.getByPlaceholderText(
      "email@example.com or username",
    );
    const passwordInput = screen.getByPlaceholderText("Enter your password");

    fireEvent.change(identifierInput, {
      target: { value: "testuser@example.com" },
    });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    expect(identifierInput).toHaveValue("testuser@example.com");
    expect(passwordInput).toHaveValue("password123");
  });

  test("submits successfully and closes the modal", async () => {
    mockLogin.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      token_type: "bearer",
    });

    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={switchToSignUp}
      />,
    );

    fireEvent.change(
      screen.getByPlaceholderText("email@example.com or username"),
      { target: { value: "testuser@example.com" } },
    );
    fireEvent.change(screen.getByPlaceholderText("Enter your password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        identifier: "testuser@example.com",
        password: "password123",
      });
    });
    expect(authLogin).toHaveBeenCalledWith("access", "refresh", "bearer");
    expect(mockOnClose).toHaveBeenCalled();
    expect(push).toHaveBeenCalled();
  });

  test("closes when clicking the overlay", () => {
    render(
      <SignInModal
        isOpen={true}
        onClose={mockOnClose}
        switchToSignUp={switchToSignUp}
      />,
    );

    fireEvent.click(
      screen.getByRole("heading", { name: /sign in/i }).closest("div")!
        .parentElement!,
    );

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
