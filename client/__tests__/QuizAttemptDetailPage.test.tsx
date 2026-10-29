import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import QuizAttemptDetailPage from "@features/quiz-attempts/pages/QuizAttemptDetailPage";
import { getQuizAttempt } from "@features/quiz-history/api/quizHistoryApi";

let mockUserId = "user-1";
let mockAttemptId = "attempt-1";

jest.mock("next/router", () => ({
  useRouter: () => ({ query: { attemptId: mockAttemptId }, push: jest.fn() }),
}));
jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({ user: { id: mockUserId } }),
}));
jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@features/quiz-history/api/quizHistoryApi", () => ({ getQuizAttempt: jest.fn() }));
jest.mock("react-hot-toast", () => ({
  __esModule: true, default: { error: jest.fn() },
}));
jest.mock("@features/quiz/components/NavBar", () => ({ __esModule: true, default: () => <nav /> }));
jest.mock("@features/quiz/components/Footer", () => ({ __esModule: true, default: () => <footer /> }));

const mockGetAttempt = getQuizAttempt as jest.Mock;
const attempt = {
  quiz_title: "Network practice", score: 1, percentage: 100, total_questions: 1,
  question_results: [{ question: "Q1", user_answer: "A", correct_answer: "A",
    question_type: "multichoice", is_correct: true, result: "Correct" }],
};

describe("QuizAttemptDetailPage", () => {
  beforeEach(() => {
    mockUserId = "user-1";
    mockAttemptId = "attempt-1";
    mockGetAttempt.mockReset().mockResolvedValue(attempt);
  });
  afterEach(() => jest.restoreAllMocks());

  test("shows saved scores and answer feedback", async () => {
    render(<QuizAttemptDetailPage />);
    expect(await screen.findByText("Network practice")).toBeInTheDocument();
    expect(screen.getByText(/Score: 1\/1/)).toBeInTheDocument();
    expect(screen.getByText("Your answer:")).toBeInTheDocument();
    expect(screen.getByText("Correct answer:")).toBeInTheDocument();
  });

  test("clears old results before loading a different account or attempt", async () => {
    const { rerender } = render(<QuizAttemptDetailPage />);
    expect(await screen.findByText("Network practice")).toBeInTheDocument();
    mockUserId = "user-2";
    mockAttemptId = "attempt-2";
    mockGetAttempt.mockResolvedValue({ ...attempt, quiz_title: "New practice" });
    rerender(<QuizAttemptDetailPage />);
    expect(screen.queryByText("Network practice")).not.toBeInTheDocument();
    expect(await screen.findByText("New practice")).toBeInTheDocument();
    expect(mockGetAttempt).toHaveBeenLastCalledWith("attempt-2");
  });

  test("allows retry after a failed detail request", async () => {
    jest.spyOn(console, "error").mockImplementation(() => {});
    mockGetAttempt.mockRejectedValueOnce(new Error("network unavailable"));
    render(<QuizAttemptDetailPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load this graded attempt.");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Network practice")).toBeInTheDocument();
  });
});
