import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SignInModal from "../components/auth/SignInModal";

const mockLogin = jest.fn();
const mockAuthLogin = jest.fn();

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    login: (...args: any[]) => mockLogin(...args),
  };
});

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({ login: mockAuthLogin }),
}));

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

describe("SignInModal UI", () => {
  const onClose = jest.fn();
  const switchToSignUp = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("validates identifier and password", async () => {
    render(
      <SignInModal isOpen onClose={onClose} switchToSignUp={switchToSignUp} />,
    );

    fireEvent.submit(
      screen.getByRole("button", { name: /sign in/i }).closest("form")!,
    );

    expect(
      await screen.findByText(/Email or username is required/i),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/email@example.com/i), {
      target: { value: "user" },
    });
    fireEvent.submit(
      screen.getByRole("button", { name: /sign in/i }).closest("form")!,
    );

    expect(
      await screen.findByText(/Password is required/i),
    ).toBeInTheDocument();
  });

  test("shows server error", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid credentials"));

    render(
      <SignInModal isOpen onClose={onClose} switchToSignUp={switchToSignUp} />,
    );

    fireEvent.change(screen.getByPlaceholderText(/email@example.com/i), {
      target: { value: "user" },
    });
    fireEvent.change(screen.getByPlaceholderText(/password/i), {
      target: { value: "bad" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
    });
  });
});
