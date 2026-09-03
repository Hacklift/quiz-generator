import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import ParentDashboard from "@features/dashboard/school/views/ParentDashboard";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

jest.mock("next/router", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("@features/persona/hooks/useTerms", () => ({
  useTerms: () => (key: string) =>
    key === "learner" ? "child" : key === "assignment" ? "practice set" : key,
}));
jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: { listLiveQuizzes: jest.fn() },
}));

const listLiveQuizzes = liveQuizService.listLiveQuizzes as jest.Mock;
const props = {
  persona: { category: "school", userType: "parent" } as const,
  user: {
    id: "parent-1",
    username: "pat",
    email: "pat@example.com",
    is_verified: true,
  },
};

describe("ParentDashboard", () => {
  beforeEach(() => listLiveQuizzes.mockReset());

  test("shows the create action and empty state", async () => {
    listLiveQuizzes.mockResolvedValue([]);
    render(<ParentDashboard {...props} />);
    expect(screen.getByRole("link", { name: "Create Practice" })).toHaveAttribute(
      "href",
      "/parent-practice/new",
    );
    expect(await screen.findByText(/No practice yet/)).toBeInTheDocument();
  });

  test("shows completed attempts, latest score, and result link", async () => {
    listLiveQuizzes.mockResolvedValue([
      {
        quiz_id: "quiz-1",
        title: "Multiplication Tables",
        status: "active",
        participant_count: 2,
        completed_count: 2,
        latest_score: 8,
        latest_percentage: 80,
      },
    ]);
    render(<ParentDashboard {...props} />);
    expect(await screen.findByText("Multiplication Tables")).toBeInTheDocument();
    expect(screen.getByText(/2 completed attempts · Latest: 8 \(80%\)/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View results" })).toHaveAttribute(
      "href",
      "/my-live-quizzes/quiz-1",
    );
    await waitFor(() => expect(listLiveQuizzes).toHaveBeenCalledTimes(1));
  });
});
