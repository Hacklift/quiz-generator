import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SignUpModal from "../components/auth/SignUpModal";

const mockRegisterUser = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    registerUser: (...args: any[]) => mockRegisterUser(...args),
  };
});

describe("SignUpModal", () => {
  const onClose = jest.fn();
  const switchToSignIn = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("validates username/email/password/confirm password", async () => {
    render(
      <SignUpModal isOpen onClose={onClose} switchToSignIn={switchToSignIn} />,
    );

    fireEvent.change(screen.getByPlaceholderText("Enter Username"), {
      target: { value: "ab" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Full Name"), {
      target: { value: "Jo" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Email"), {
      target: { value: "invalid" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Password"), {
      target: { value: "short" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm Password"), {
      target: { value: "different" },
    });

    expect(
      await screen.findByText(/Username must be at least 3 characters/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Full name must be at least 3 characters/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/valid email address/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Password must be at least 8 characters/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
  });

  test("success resets fields and opens verify modal", async () => {
    mockRegisterUser.mockResolvedValue({});

    render(
      <SignUpModal isOpen onClose={onClose} switchToSignIn={switchToSignIn} />,
    );

    fireEvent.change(screen.getByPlaceholderText("Enter Username"), {
      target: { value: "john" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Full Name"), {
      target: { value: "John Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Email"), {
      target: { value: "john@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Password"), {
      target: { value: "Abcd1234!" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm Password"), {
      target: { value: "Abcd1234!" },
    });

    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    await waitFor(() => {
      expect(screen.getByText(/Verify Your Email/i)).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText("Enter Username")).toHaveValue("");
    expect(screen.getByPlaceholderText("Enter Full Name")).toHaveValue("");
    expect(screen.getByPlaceholderText("Enter Email")).toHaveValue("");
  });
});
