import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DisplayQuiz from "@features/quiz/pages/QuizDisplayPage";
import publicApi from "@shared/api/publicHttp";
import toast from "react-hot-toast";

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: () => null,
  }),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@shared/api/publicHttp", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock("@shared/api/http", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

jest.mock("@shared/auth/tokenService", () => ({
  TokenService: {
    hasTokens: () => false,
  },
}));

jest.mock("@features/quiz-history/api/saveQuizToHistoryApi", () => ({
  saveQuizToHistory: jest.fn(),
}));

jest.mock("@features/live-quiz/components/LiveQuizAccessCodePanel", () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock("@features/quiz/components", () => {
  const QuizAnswerField =
    require("@features/quiz/components/QuizAnswerField").default;

  return {
    CheckButton: ({ onClick }: { onClick: () => void }) => (
      <button type="button" onClick={onClick}>
        Check Quiz
      </button>
    ),
    NewQuizButton: () => <button type="button">New Quiz</button>,
    QuizAnswerField,
    DownloadQuizButton: () => <div>Download Quiz</div>,
    NavBar: () => <div>NavBar</div>,
    Footer: () => <div>Footer</div>,
    ShareButton: () => <div>Share Quiz</div>,
    SaveQuizButton: () => <div>Save Quiz</div>,
  };
});

const mockPublicApiPost = publicApi.post as jest.Mock;
const mockToastError = toast.error as jest.Mock;
const mockToastSuccess = toast.success as jest.Mock;

const storedQuiz = {
  title: "Capitals Quiz",
  question_type: "multichoice",
  questions: [
    {
      question: "What is the capital of France?",
      options: ["A) Paris", "B) London"],
      answer: "A) Paris",
      question_type: "multichoice",
    },
    {
      question: "What is the capital of Spain?",
      options: ["A) Madrid", "B) Rome"],
      answer: "A) Madrid",
      question_type: "multichoice",
    },
  ],
};

describe("QuizDisplayPage", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("saved_quiz_view", JSON.stringify(storedQuiz));
    mockPublicApiPost.mockReset();
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
  });

  test("prompts the user instead of grading when questions are unanswered", async () => {
    render(<DisplayQuiz />);

    expect(
      await screen.findByText("1. What is the capital of France?"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    expect(mockPublicApiPost).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith(
      "Answer the quiz before submitting it for grading.",
    );
  });

  test("locks submitted answers after grading", async () => {
    mockPublicApiPost.mockResolvedValue({
      data: [
        {
          question: "What is the capital of France?",
          user_answer: "A) Paris",
          correct_answer: "A) Paris",
          result: "Correct",
          is_correct: true,
          question_type: "multichoice",
        },
        {
          question: "What is the capital of Spain?",
          user_answer: "A) Madrid",
          correct_answer: "A) Madrid",
          result: "Correct",
          is_correct: true,
          question_type: "multichoice",
        },
      ],
    });

    render(<DisplayQuiz />);

    const radioButtons = await screen.findAllByRole("radio");

    fireEvent.click(radioButtons[0]);
    fireEvent.click(radioButtons[2]);
    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    await waitFor(() => {
      expect(screen.getByText("My Quiz Result")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Check Quiz" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Answers are locked after submission and grading."),
    ).toBeInTheDocument();
    screen.getAllByRole("radio").forEach((radio) => {
      expect(radio).toBeDisabled();
    });
  });
});
