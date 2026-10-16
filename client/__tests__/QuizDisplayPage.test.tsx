import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import DisplayQuiz from "@features/quiz/pages/QuizDisplayPage";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { TokenService } from "@shared/auth/tokenService";
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

jest.mock("@shared/api/http", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

jest.mock("@shared/auth/tokenService", () => ({
  TokenService: {
    hasTokens: jest.fn(),
  },
}));

jest.mock("@shared/api/publicHttp", () => ({
  __esModule: true,
  default: { post: jest.fn() },
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
const mockPublicPost = publicApi.post as jest.Mock;
const mockHasTokens = TokenService.hasTokens as jest.Mock;
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
    localStorage.clear();
    localStorage.setItem("saved_quiz_view", JSON.stringify(storedQuiz));
    mockApiPost.mockReset();
    mockPublicPost.mockReset();
    mockHasTokens.mockReturnValue(true);
    mockToastError.mockReset();
    mockToastSuccess.mockReset();
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
    expect(mockApiPost).toHaveBeenCalledTimes(1);
    expect(mockPublicPost).not.toHaveBeenCalled();
  });

  test("grades guests with the public client", async () => {
    mockHasTokens.mockReturnValue(false);
    mockPublicPost.mockResolvedValue({ data: [], headers: { "x-quiz-attempt-status": "not-requested" } });
    render(<DisplayQuiz />);
    const radios = await screen.findAllByRole("radio");
    fireEvent.click(radios[0]);
    fireEvent.click(radios[2]);
    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    expect(await screen.findByText("My Quiz Result")).toBeInTheDocument();
    expect(mockPublicPost).toHaveBeenCalledTimes(1);
    expect(mockApiPost).not.toHaveBeenCalled();
    expect(mockToastError).not.toHaveBeenCalled();
  });

  test("keeps scores visible and warns when attempt storage fails", async () => {
    mockApiPost.mockResolvedValue({ data: [], headers: { "x-quiz-attempt-status": "failed" } });
    render(<DisplayQuiz />);
    const radios = await screen.findAllByRole("radio");
    fireEvent.click(radios[0]);
    fireEvent.click(radios[2]);
    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    expect(await screen.findByText("My Quiz Result")).toBeInTheDocument();
    expect(mockToastError).toHaveBeenCalledWith(
      "Your quiz was graded, but this attempt could not be saved to history.",
    );
  });

  test("prevents duplicate submissions and freezes answers while grading", async () => {
    let resolveGrade!: (value: unknown) => void;
    mockApiPost.mockReturnValue(new Promise((resolve) => { resolveGrade = resolve; }));
    render(<DisplayQuiz />);
    const radios = await screen.findAllByRole("radio");
    fireEvent.click(radios[0]);
    fireEvent.click(radios[2]);
    const submit = screen.getByRole("button", { name: "Check Quiz" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(mockApiPost).toHaveBeenCalledTimes(1);
    radios.forEach((radio) => expect(radio).toBeDisabled());
    resolveGrade({ data: [] });
    expect(await screen.findByText("My Quiz Result")).toBeInTheDocument();
  });

  test("renders per-question correctness, correct answers, and explanations after submission", async () => {
    mockApiPost.mockResolvedValue({
      data: [
        {
          question: "What is the capital of France?",
          user_answer: "A) Paris",
          correct_answer: "A) Paris",
          result: "Correct",
          is_correct: true,
          question_type: "multichoice",
          explanation: "Paris has been the capital of France since the 10th century.",
        },
        {
          question: "What is the capital of Spain?",
          user_answer: "B) Rome",
          correct_answer: "A) Madrid",
          result: "Incorrect",
          is_correct: false,
          question_type: "multichoice",
          explanation: "Madrid is the capital of Spain, whereas Rome is in Italy.",
        },
      ],
    });

    render(<DisplayQuiz />);

    const radioButtons = await screen.findAllByRole("radio");
    fireEvent.click(radioButtons[0]);
    fireEvent.click(radioButtons[3]);
    fireEvent.click(screen.getByRole("button", { name: "Check Quiz" }));

    await waitFor(() => {
      expect(screen.getByText("My Quiz Result")).toBeInTheDocument();
    });

    // Check score badges
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();

    // Check explanations in the DOM
    expect(
      screen.getAllByText("Paris has been the capital of France since the 10th century.").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Madrid is the capital of Spain, whereas Rome is in Italy.").length,
    ).toBeGreaterThan(0);

    // Check correctness badges
    expect(screen.getAllByText("✓ Correct").length).toBeGreaterThan(0);
    expect(screen.getAllByText("✗ Incorrect").length).toBeGreaterThan(0);
  });
});

