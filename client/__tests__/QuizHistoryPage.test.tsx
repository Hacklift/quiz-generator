import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import DisplayQuizHistory from "@features/quiz-history/pages/QuizHistoryPage";
import {
  deleteQuizHistoryItem,
  getUserQuizHistory,
} from "@features/quiz-history/api/quizHistoryApi";
import toast from "react-hot-toast";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@features/quiz-history/api/quizHistoryApi", () => ({
  getUserQuizHistory: jest.fn(),
  deleteQuizHistoryItem: jest.fn(),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
  }),
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

const mockGetUserQuizHistory = getUserQuizHistory as jest.Mock;
const mockDeleteQuizHistoryItem = deleteQuizHistoryItem as jest.Mock;
const mockToastSuccess = toast.success as jest.Mock;
const mockToastError = toast.error as jest.Mock;

const attemptHistory = [
  {
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
  },
];

describe("QuizHistoryPage", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockGetUserQuizHistory.mockReset();
    mockDeleteQuizHistoryItem.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
    mockGetUserQuizHistory.mockResolvedValue(attemptHistory);
    mockDeleteQuizHistoryItem.mockResolvedValue({
      message: "Quiz attempt deleted successfully",
    });
  });

  test("renders scored attempts and routes to the detail page", async () => {
    render(<DisplayQuizHistory openLoginModal={jest.fn()} />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    expect(screen.getByText(/Score: 1\/2 · 50%/)).toBeInTheDocument();
    expect(
      screen.getByText(/What protocol serves web pages\?/),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Correct answer:/)).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));

    expect(mockPush).toHaveBeenCalledWith("/quiz_history/attempt-1");
  });

  test("deletes an attempt after confirmation and removes it from the page", async () => {
    render(<DisplayQuizHistory openLoginModal={jest.fn()} />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    const dialog = screen.getByText("Confirm Delete").closest("div");
    expect(dialog).not.toBeNull();

    fireEvent.click(
      within(dialog as HTMLElement).getByRole("button", { name: "Delete" }),
    );

    await waitFor(() => {
      expect(mockDeleteQuizHistoryItem).toHaveBeenCalledWith("attempt-1");
    });
    expect(mockToastSuccess).toHaveBeenCalledWith("Quiz attempt deleted.");

    await waitFor(() => {
      expect(screen.queryByText("Networking Basics")).not.toBeInTheDocument();
    });
    expect(
      screen.getByText("No graded quiz attempts available yet."),
    ).toBeInTheDocument();
  });
});
