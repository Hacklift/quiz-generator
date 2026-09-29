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

const generatedHistory = [
  {
    id: "history-1",
    quiz_id: "quiz-1",
    quiz_name: "Networking Basics",
    profession: "Networking Basics",
    created_at: "2026-08-20T10:00:00.000Z",
    question_type: "multichoice",
    difficulty_level: "medium",
    live_quiz_enabled: true,
    live_quiz_stats: {
      invited_participants: 4,
      joined_participants: 3,
      completed_participants: 2,
      average_score: 75,
      best_score: 100,
      quiz_status: "active",
    },
    questions: [
      {
        question: "What protocol serves web pages?",
        options: ["HTTP", "SSH"],
        answer: "HTTP",
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
    mockGetUserQuizHistory.mockResolvedValue(generatedHistory);
    mockDeleteQuizHistoryItem.mockResolvedValue({
      message: "Quiz history item deleted successfully",
    });
  });

  test("renders generated history and preserves live-dashboard and detail actions", async () => {
    render(<DisplayQuizHistory openLoginModal={jest.fn()} />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    expect(screen.getByText(/multichoice · medium/)).toBeInTheDocument();
    expect(
      screen.getByText(/What protocol serves web pages\?/),
    ).toBeInTheDocument();
    expect(screen.getByText("SSH")).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent === "Answer: HTTP"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Live Dashboard" }));

    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes/quiz-1");

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));

    expect(mockPush).toHaveBeenCalledWith("/quiz_history/history-1");

    fireEvent.click(
      screen.getByRole("button", { name: "View graded attempts" }),
    );

    expect(mockPush).toHaveBeenCalledWith("/quiz_attempts");
  });

  test("deletes generated history after confirmation and removes it from the page", async () => {
    render(<DisplayQuizHistory openLoginModal={jest.fn()} />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    const dialog = screen.getByText("Confirm Delete").closest("div");
    expect(dialog).not.toBeNull();

    fireEvent.click(
      within(dialog as HTMLElement).getByRole("button", { name: "Delete" }),
    );

    await waitFor(() => {
      expect(mockDeleteQuizHistoryItem).toHaveBeenCalledWith("history-1");
    });
    expect(mockToastSuccess).toHaveBeenCalledWith("Quiz history item deleted.");

    await waitFor(() => {
      expect(screen.queryByText("Networking Basics")).not.toBeInTheDocument();
    });
    expect(screen.getByText("No quiz history available.")).toBeInTheDocument();
  });
});
