import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import QuizAttemptsPage from "@features/quiz-attempts/pages/QuizAttemptsPage";
import {
  deleteQuizAttempt,
  getUserQuizAttempts,
} from "@features/quiz-history/api/quizHistoryApi";

const mockPush = jest.fn();
let mockUserId = "user-1";
let mockAuthenticated = true;

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ user: { id: mockUserId } }),
}));

jest.mock("next/router", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("@features/quiz-history/api/quizHistoryApi", () => ({
  getUserQuizAttempts: jest.fn(),
  deleteQuizAttempt: jest.fn(),
}));

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => mockAuthenticated ? <>{children}</> : <p>Sign in</p>,
}));

jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav>NavBar</nav>,
}));

jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer>Footer</footer>,
}));

const mockGetUserQuizAttempts = getUserQuizAttempts as jest.Mock;
const mockDeleteQuizAttempt = deleteQuizAttempt as jest.Mock;

describe("QuizAttemptsPage", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockUserId = "user-1";
    mockAuthenticated = true;
    mockGetUserQuizAttempts.mockReset();
    mockGetUserQuizAttempts.mockResolvedValue([
      {
        id: "attempt-1",
        quiz_id: "quiz-1",
        quiz_title: "Networking Basics",
        score: 1,
        percentage: 50,
        total_questions: 2,
        submitted_at: "2026-08-20T10:00:00.000Z",
      },
    ]);
    mockDeleteQuizAttempt.mockResolvedValue({
      message: "Quiz attempt deleted successfully",
    });
    jest.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test("keeps attempt actions on the dedicated attempts route", async () => {
    render(<QuizAttemptsPage />);

    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    expect(screen.getByText(/Score: 1\/2 · 50%/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View Details" }));
    expect(mockPush).toHaveBeenCalledWith("/quiz_attempts/attempt-1");

    fireEvent.click(screen.getByRole("button", { name: "Retake Quiz" }));
    expect(mockPush).toHaveBeenCalledWith("/quiz_display?quizId=quiz-1");

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => {
      expect(mockDeleteQuizAttempt).toHaveBeenCalledWith("attempt-1");
    });
    expect(
      screen.getByText("No graded quiz attempts available yet."),
    ).toBeInTheDocument();
  });

  test("fetches attempts only after authentication is ready", async () => {
    mockAuthenticated = false;
    const { rerender } = render(<QuizAttemptsPage />);
    expect(mockGetUserQuizAttempts).not.toHaveBeenCalled();
    mockAuthenticated = true;
    rerender(<QuizAttemptsPage />);
    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
  });

  test("clears previous account attempts when the user changes", async () => {
    const { rerender } = render(<QuizAttemptsPage />);
    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
    mockUserId = "user-2";
    mockGetUserQuizAttempts.mockResolvedValue([]);
    rerender(<QuizAttemptsPage />);
    expect(screen.queryByText("Networking Basics")).not.toBeInTheDocument();
    expect(await screen.findByText("No graded quiz attempts available yet.")).toBeInTheDocument();
  });

  test("offers retry rather than presenting a failed fetch as empty history", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    mockGetUserQuizAttempts.mockRejectedValueOnce(new Error("network unavailable"));
    render(<QuizAttemptsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load your graded attempts.");
    expect(screen.queryByText("No graded quiz attempts available yet.")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Networking Basics")).toBeInTheDocument();
  });
});
