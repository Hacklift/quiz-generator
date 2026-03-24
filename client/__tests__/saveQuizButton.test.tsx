import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SaveQuizButton from "../components/home/SaveQuizButton";

const mockSaveQuiz = jest.fn();
const mockUseAuth = jest.fn();
const mockGetAccessToken = jest.fn();
const toastError = jest.fn();
const toastSuccess = jest.fn();

jest.mock("../lib/functions/savedQuiz", () => ({
  saveQuiz: (...args: unknown[]) => mockSaveQuiz(...args),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("../lib/functions/tokenService", () => ({
  TokenService: {
    getAccessToken: (...args: unknown[]) => mockGetAccessToken(...args),
  },
}));

jest.mock("../components/auth/SignInModal", () => () => (
  <div data-testid="signin-modal" />
));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    error: (...args: unknown[]) => toastError(...args),
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}));

describe("SaveQuizButton", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: "user-1" } });
    mockGetAccessToken.mockReturnValue("access-token");
  });

  test("validates title before saving", async () => {
    render(
      <SaveQuizButton
        quizData={[{ question: "Q1", question_type: "multichoice" }]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /save quiz/i }));
    fireEvent.click(screen.getByRole("button", { name: "✓" }));

    expect(toastError).toHaveBeenCalledWith("Please enter a quiz title.");
    expect(mockSaveQuiz).not.toHaveBeenCalled();
  });

  test("saves quiz with formatted payload", async () => {
    mockSaveQuiz.mockResolvedValue({});

    render(
      <SaveQuizButton
        quizData={[
          { question: "Q1", options: ["A", "B"], question_type: "multichoice" },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /save quiz/i }));
    fireEvent.change(screen.getByPlaceholderText("Enter title"), {
      target: { value: "My Quiz" },
    });
    fireEvent.click(screen.getByRole("button", { name: "✓" }));

    await waitFor(() => {
      expect(mockSaveQuiz).toHaveBeenCalledWith(
        "My Quiz",
        "multichoice",
        [{ question: "Q1", options: ["A", "B"], question_type: "multichoice" }],
        "access-token",
        undefined,
      );
    });
    expect(toastSuccess).toHaveBeenCalled();
  });
});
