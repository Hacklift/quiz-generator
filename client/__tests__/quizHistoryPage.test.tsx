import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import QuizHistoryPage from "../pages/quiz_history";

const mockGetUserQuizHistory = jest.fn();
const mockUseAuth = jest.fn();

jest.mock("../lib/functions/getUserQuizHistory", () => ({
  getUserQuizHistory: (...args: unknown[]) => mockGetUserQuizHistory(...args),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("../components/home/NavBar", () => () => (
  <div data-testid="navbar" />
));
jest.mock("../components/home/Footer", () => () => (
  <div data-testid="footer" />
));
jest.mock(
  "../components/auth/RequireAuth",
  () =>
    ({ children }: { children: React.ReactNode }) => <>{children}</>,
);

describe("QuizHistoryPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders no history message when empty", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    mockGetUserQuizHistory.mockResolvedValue([]);

    render(<QuizHistoryPage openLoginModal={() => {}} />);

    await waitFor(() => {
      expect(
        screen.getByText("No quiz history available."),
      ).toBeInTheDocument();
    });
  });

  test("renders fetched history entries", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false });
    mockGetUserQuizHistory.mockResolvedValue([
      {
        created_at: new Date().toISOString(),
        questions: [
          { question: "What is 2+2?", answer: "4", options: ["3", "4"] },
        ],
      },
    ]);

    render(<QuizHistoryPage openLoginModal={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/What is 2\+2\?/i)).toBeInTheDocument();
      expect(screen.getByText(/Answer:/i)).toBeInTheDocument();
    });
  });
});
