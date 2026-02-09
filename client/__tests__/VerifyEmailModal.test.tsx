import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import VerifyEmailModal from "../components/auth/VerifyEmailModal";

const mockResend = jest.fn();

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    resendVerification: (...args: any[]) => mockResend(...args),
  };
});

describe("VerifyEmailModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("resend button triggers resend call", async () => {
    mockResend.mockResolvedValue({});

    render(
      <VerifyEmailModal
        isOpen
        onClose={jest.fn()}
        userEmail="user@example.com"
        onVerified={jest.fn()}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Resend Verification Email/i }),
    );

    await waitFor(() => {
      expect(mockResend).toHaveBeenCalledWith("user@example.com");
    });
  });
});
