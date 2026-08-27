import React from "react";
import { render, screen } from "@testing-library/react";
import QuizHistoryDetailsPage from "@features/quiz-history/pages/QuizHistoryDetailPage";
import { getQuizHistoryItem } from "@features/quiz-history/api/quizHistoryApi";

let mockQuery: { historyId?: string | string[] } = { historyId: "attempt-1" };
const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push: mockPush, query: mockQuery }),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    error: jest.fn(),
  },
}));

jest.mock("@features/quiz-history/api/quizHistoryApi", () => ({
  getQuizHistoryItem: jest.fn(),
}));

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav>NavBar</nav>,
}));

jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer>Footer</footer>,
}));

const mockGetQuizHistoryItem = getQuizHistoryItem as jest.Mock;

describe("QuizHistoryDetailPage", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockGetQuizHistoryItem.mockReset();
    mockQuery = { historyId: "attempt-1" };
  });

  test("renders the scored-attempt detail view", async () => {
    mockGetQuizHistoryItem.mockResolvedValue({
      id: "attempt-1",
      quiz_id: "quiz-1",
      quiz_title: "Networking Basics",
      score: 1,
      percentage: 50,
      total_questions: 2,
      submitted_at: "2026-08-20T10:00:00.000Z",
      question_results: [
        {
          question: "What protocol serves web pages?",
          user_answer: "HTTP",
          correct_answer: "HTTP",
          question_type: "multichoice",
          is_correct: true,
          result: "Correct",
        },
        {
          question: "Which port is commonly used for HTTPS?",
          user_answer: "80",
          correct_answer: "443",
          question_type: "multichoice",
          accuracy_percentage: 25,
          is_correct: false,
          result: "Incorrect",
        },
      ],
    });

    render(<QuizHistoryDetailsPage />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    expect(screen.getByText(/Score: 1\/2/)).toBeInTheDocument();
    expect(screen.getByText(/Percentage: 50%/)).toBeInTheDocument();
    expect(
      screen.getByText(/Which port is commonly used for HTTPS\?/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Accuracy:/)).toBeInTheDocument();
  });

  test("renders the legacy generated-history detail view", async () => {
    mockQuery = { historyId: "history-1" };
    mockGetQuizHistoryItem.mockResolvedValue({
      id: "history-1",
      quiz_id: "quiz-legacy-1",
      created_at: "2026-08-19T15:00:00.000Z",
      quiz_name: "Biology Revision",
      question_type: "multichoice",
      difficulty_level: "medium",
      profession: "Biology Revision",
      audience_type: "students",
      custom_instruction: "Focus on cell biology",
      questions: [
        {
          question: "What is the powerhouse of the cell?",
          options: ["Nucleus", "Mitochondria"],
          answer: "Mitochondria",
        },
      ],
    });

    render(<QuizHistoryDetailsPage />);

    expect(await screen.findByText("Biology Revision")).toBeInTheDocument();
    expect(screen.getByText(/Generated on:/)).toBeInTheDocument();
    expect(screen.getByText(/Question type: multichoice/)).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) =>
          element?.textContent === "Custom instruction: Focus on cell biology",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, element) => element?.textContent === "Answer: Mitochondria",
      ),
    ).toBeInTheDocument();
  });
});
