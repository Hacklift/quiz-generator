import React from "react";
import { render, screen } from "@testing-library/react";
import LiveQuizAttemptDetailPage from "@features/live-quiz/pages/LiveQuizAttemptDetailPage";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav>Nav</nav>,
}));
jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer>Footer</footer>,
}));
jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: { getAttemptDetail: jest.fn() },
}));

const getAttemptDetail = liveQuizService.getAttemptDetail as jest.Mock;

test("renders score and correct/incorrect status for every question", async () => {
  getAttemptDetail.mockResolvedValue({
    session_id: "session-1",
    quiz_id: "quiz-1",
    title: "Multiplication Tables",
    participant_name: "Sam",
    score: 1,
    total_questions: 2,
    percentage: 50,
    submitted_at: "2026-08-25T10:00:00Z",
    auto_submitted: false,
    graded_answers: [
      { question_index: 0, question: "2 × 3?", selected_answer: "6", correct_answer: "6", question_type: "multichoice", is_correct: true },
      { question_index: 1, question: "4 × 4?", selected_answer: "14", correct_answer: "16", question_type: "multichoice", is_correct: false },
    ],
  });

  render(<LiveQuizAttemptDetailPage quizId="quiz-1" sessionId="session-1" />);
  expect(await screen.findByText("1/2")).toBeInTheDocument();
  expect(screen.getByText("50%")).toBeInTheDocument();
  expect(screen.getByLabelText("Correct")).toHaveTextContent("✓");
  expect(screen.getByLabelText("Incorrect")).toHaveTextContent("✗");
  expect(screen.getByText("Child's answer: 14")).toBeInTheDocument();
  expect(screen.getByText("Correct answer: 16")).toBeInTheDocument();
});
