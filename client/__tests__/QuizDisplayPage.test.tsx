import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DisplayQuiz from "@features/quiz/pages/QuizDisplayPage";
import { api } from "@shared/api/http";
import toast from "react-hot-toast";

let mockIsAuthenticated = true;

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

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated }),
}));

jest.mock("@features/auth/components/SignInModal", () => ({
  __esModule: true,
  default: ({
    isOpen,
    onSuccess,
  }: {
    isOpen: boolean;
    onSuccess?: () => void | Promise<void>;
  }) =>
    isOpen ? (
      <div role="dialog" aria-label="Sign in required">
        <button type="button" onClick={() => void onSuccess?.()}>
          Complete sign in
        </button>
      </div>
    ) : null,
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

const mockApiPost = api.post as jest.Mock;
const mockToastError = toast.error as jest.Mock;
const mockToastSuccess = toast.success as jest.Mock;

const storedQuiz = {
  quiz_id: "quiz-123",
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
    mockIsAuthenticated = true;
    localStorage.clear();
    localStorage.setItem("saved_quiz_view", JSON.stringify(storedQuiz));
    mockApiPost.mockReset();
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
  });

  test("requires sign-in before grading and preserves answers through sign-in", async () => {
    mockIsAuthenticated = false;
    mockApiPost.mockResolvedValue({
      data: {
        question_results: storedQuiz.questions.map((question, question_index) => ({
          question_index,
          question: question.question,
          user_answer: question.answer,
          correct_answer: question.answer,
          result: "Correct",
          is_correct: true,
          question_type: "multichoice",
        })),
      },
    });
    render(<DisplayQuiz />);

    const radioButtons = await screen.findAllByRole("radio");
    fireEvent.click(radioButtons[0]);
    fireEvent.click(radioButtons[2]);
    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    expect(mockApiPost).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith(
      "Sign in to submit this quiz and receive or save your result.",
    );
    expect(
      screen.getByRole("dialog", { name: "Sign in required" }),
    ).toBeInTheDocument();
    expect(radioButtons[0]).toBeChecked();
    expect(radioButtons[2]).toBeChecked();

    fireEvent.click(screen.getByRole("button", { name: "Complete sign in" }));

    await waitFor(() => expect(mockApiPost).toHaveBeenCalledTimes(1));
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/quizzes/quiz-123/grade",
      {
        answers: [
          { question_index: 0, user_answer: "A) Paris" },
          { question_index: 1, user_answer: "A) Madrid" },
        ],
      },
    );
    expect(await screen.findByText("My Quiz Result")).toBeInTheDocument();
  });

  test("prompts the user instead of grading when questions are unanswered", async () => {
    render(<DisplayQuiz />);

    expect(
      await screen.findByText("1. What is the capital of France?"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    expect(mockApiPost).not.toHaveBeenCalled();
    expect(mockToastError).toHaveBeenCalledWith(
      "Answer the quiz before submitting it for grading.",
    );
  });

  test("locks submitted answers after grading", async () => {
    mockApiPost.mockResolvedValue({
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
