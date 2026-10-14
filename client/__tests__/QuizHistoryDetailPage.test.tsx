import React from "react";
import { render, screen } from "@testing-library/react";
import QuizHistoryDetailsPage from "@features/quiz-history/pages/QuizHistoryDetailPage";
import { getQuizHistoryItem } from "@features/quiz-history/api/quizHistoryApi";

let mockQuery: { historyId?: string | string[] } = { historyId: "history-1" };
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
    mockQuery = { historyId: "history-1" };
  });

  test("renders generated-history details and preserves the live dashboard action", async () => {
    mockGetQuizHistoryItem.mockResolvedValue({
      id: "history-1",
      quiz_id: "quiz-1",
      quiz_name: "Networking Basics",
      profession: "Networking Basics",
      created_at: "2026-08-20T10:00:00.000Z",
      question_type: "multichoice",
      difficulty_level: "medium",
      audience_type: "students",
      live_quiz_enabled: true,
      live_quiz_stats: {
        invited_participants: 4,
        joined_participants: 3,
        completed_participants: 2,
        quiz_status: "active",
      },
      questions: [
        {
          question: "What protocol serves web pages?",
          options: ["HTTP", "SSH"],
          answer: "HTTP",
        },
      ],
    });

    render(<QuizHistoryDetailsPage />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    expect(screen.getByText(/Generated on:/)).toBeInTheDocument();
    expect(screen.getByText("SSH")).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent === "Answer: HTTP"),
    ).toBeInTheDocument();

    screen.getByRole("button", { name: "Open Live Dashboard" }).click();
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes/quiz-1");
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
