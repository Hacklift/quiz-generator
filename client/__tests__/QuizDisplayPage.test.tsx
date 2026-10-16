import React from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import { createLocaleI18n } from "@features/locale/i18n";
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
    DownloadQuizButton: ({ contentLocale }: { contentLocale?: string }) => (
      <div data-testid="download-quiz" data-locale={contentLocale}>
        Download Quiz
      </div>
    ),
    NavBar: () => <div>NavBar</div>,
    Footer: () => <div>Footer</div>,
    ShareButton: () => <div>Share Quiz</div>,
    SaveQuizButton: ({ contentLocale }: { contentLocale?: string }) => (
      <div data-testid="save-quiz" data-locale={contentLocale}>
        Save Quiz
      </div>
    ),
  };
});

const mockPublicApiPost = publicApi.post as jest.Mock;
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
  test("a saved French quiz retains its content and save/export language after the UI changes", async () => {
    const i18n = createLocaleI18n();
    localStorage.setItem(
      "saved_quiz_view",
      JSON.stringify({
        ...storedQuiz,
        title: "Quiz français",
        content_locale: "fr",
        questions: [
          {
            question: "Combien font deux plus deux ?",
            question_type: "true-false",
            options: ["Vrai", "Faux"],
            answer: "Vrai",
            explanation: "Deux et deux font quatre.",
          },
        ],
      }),
    );
    render(
      <I18nextProvider i18n={i18n}>
        <DisplayQuiz />
      </I18nextProvider>,
    );
    expect(await screen.findByText("Quiz français")).toBeInTheDocument();
    await act(async () => {
      await i18n.changeLanguage("es");
    });
    expect(screen.getByText("Quiz français")).toBeInTheDocument();
    expect(screen.getByText(/Combien font deux plus deux/)).toBeInTheDocument();
    expect(screen.getByText("Vrai")).toBeInTheDocument();
    expect(screen.getByText("Faux")).toBeInTheDocument();
    expect(screen.getByTestId("save-quiz")).toHaveAttribute(
      "data-locale",
      "fr",
    );
    expect(screen.getByTestId("download-quiz")).toHaveAttribute(
      "data-locale",
      "fr",
    );
  });
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
