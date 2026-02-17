import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RequestPasswordResetModal from "../components/auth/RequestPasswordResetModal";

const mockRequest = jest.fn();

jest.mock("../lib", () => {
  const actual = jest.requireActual("../lib");
  return {
    ...actual,
    requestPasswordReset: (...args: any[]) => mockRequest(...args),
  };
});

describe("RequestPasswordResetModal", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("success flow shows success state", async () => {
    mockRequest.mockResolvedValue({});

    render(
      <RequestPasswordResetModal
        isOpen
        onClose={jest.fn()}
        onRequestSuccess={jest.fn()}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText(/you@example.com/i), {
      target: { value: "user@example.com" },
    });

    fireEvent.click(screen.getByRole("button", { name: /send code/i }));

    await waitFor(() => {
      expect(screen.getByText(/Check your email/i)).toBeInTheDocument();
    });
  });
});
