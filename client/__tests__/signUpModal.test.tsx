import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SignUpModal from "../components/auth/SignUpModal";

const push = jest.fn();
const mockRegisterUser = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../lib", () => ({
  registerUser: (...args: unknown[]) => mockRegisterUser(...args),
}));

jest.mock("../components/auth/VerifyEmailModal", () => () => (
  <div data-testid="verify-email-modal" />
));

describe("SignUpModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders signup modal and toggles password visibility", () => {
    render(
      <SignUpModal
        isOpen={true}
        onClose={jest.fn()}
        switchToSignIn={jest.fn()}
      />,
    );

    const passwordInput = screen.getByPlaceholderText("Enter Password");
    expect(passwordInput).toHaveAttribute("type", "password");

    fireEvent.click(screen.getAllByRole("button")[1]);
    expect(screen.getByPlaceholderText("Enter Password")).toHaveAttribute(
      "type",
      "text",
    );
  });

  test("submits registration and shows verification modal", async () => {
    mockRegisterUser.mockResolvedValue({});

    render(
      <SignUpModal
        isOpen={true}
        onClose={jest.fn()}
        switchToSignIn={jest.fn()}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Enter Username"), {
      target: { value: "tester" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Full Name"), {
      target: { value: "Test User" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Email"), {
      target: { value: "tester@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Enter Password"), {
      target: { value: "Password1!" },
    });
    fireEvent.change(screen.getByPlaceholderText("Confirm Password"), {
      target: { value: "Password1!" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^sign up$/i }));

    await waitFor(() => {
      expect(mockRegisterUser).toHaveBeenCalledWith({
        username: "tester",
        email: "tester@example.com",
        full_name: "Test User",
        password: "Password1!",
      });
    });
    expect(screen.getByTestId("verify-email-modal")).toBeInTheDocument();
  });
});
