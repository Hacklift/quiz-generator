import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import RecentQuizzes from "@features/dashboard/components/RecentQuizzes";
import { getUserQuizHistory } from "@features/quiz-history/api/quizHistoryApi";

const authState: { user: { is_verified: boolean } | null } = {
  user: null,
};

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => authState,
}));

jest.mock("@features/quiz-history/api/quizHistoryApi", () => ({
  getUserQuizHistory: jest.fn(),
}));

describe("RecentQuizzes", () => {
  beforeEach(() => {
    authState.user = null;
    jest.mocked(getUserQuizHistory).mockReset();
  });

  test("does not request verified-only history for an unverified user", async () => {
    authState.user = { is_verified: false };
    render(<RecentQuizzes heading="Recent activity" emptyMessage="Empty" />);

    await waitFor(() => {
      expect(
        screen.getByText("Verify your email to view recent activity."),
      ).toBeInTheDocument();
    });
    expect(getUserQuizHistory).not.toHaveBeenCalled();
  });

  test("shows the persona-specific empty state for a verified user", async () => {
    authState.user = { is_verified: true };
    jest.mocked(getUserQuizHistory).mockResolvedValueOnce([]);
    render(<RecentQuizzes heading="Recent activity" emptyMessage="Empty" />);

    await waitFor(() => {
      expect(screen.getByText("Empty")).toBeInTheDocument();
    });
  });
});
