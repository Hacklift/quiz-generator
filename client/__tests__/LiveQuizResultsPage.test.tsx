import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import LiveQuizResultsPage from "@features/live-quiz/pages/LiveQuizResultsPage";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

const mockRouter = {
  query: {},
  replace: jest.fn(),
  push: jest.fn(),
};

jest.mock("next/router", () => ({
  useRouter: () => mockRouter,
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: {
    getSession: jest.fn(),
  },
}));

jest.mock("@features/live-quiz/components/GuestSignupPopup", () => ({
  __esModule: true,
  default: () => null,
}));

const mockGetSession = liveQuizService.getSession as jest.Mock;

describe("LiveQuizResultsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders question results and explanations when answers are released", async () => {
    mockGetSession.mockResolvedValue({
      session_id: "session-1",
      quiz_id: "quiz-1",
      title: "World Capitals",
      participant_name: "Alex",
      participant_email: "alex@example.com",
      status: "submitted",
      score: 1,
      total_questions: 2,
      percentage: 50,
      auto_submitted: false,
      submitted_at: "2026-10-16T10:00:00Z",
      answers_released: true,
      graded_answers: [
        {
          question_index: 0,
          question: "What is the capital of Japan?",
          selected_answer: "Tokyo",
          correct_answer: "Tokyo",
          question_type: "multichoice",
          is_correct: true,
          explanation: "Tokyo has been the capital and largest city of Japan since 1868.",
        },
        {
          question_index: 1,
          question: "What is the capital of Canada?",
          selected_answer: "Toronto",
          correct_answer: "Ottawa",
          question_type: "multichoice",
          is_correct: false,
          explanation: "Ottawa was chosen by Queen Victoria as the capital of Canada.",
        },
      ],
    });

    render(<LiveQuizResultsPage sessionId="session-1" />);

    expect(await screen.findByText("Quiz result")).toBeInTheDocument();
    expect(screen.getByText("Alex")).toBeInTheDocument();
    expect(screen.getByText("1/2")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();

    // Check Question Results header
    expect(screen.getByText("Question Results & Explanations")).toBeInTheDocument();

    // Check Question items
    expect(screen.getByText("1. What is the capital of Japan?")).toBeInTheDocument();
    expect(screen.getByText("2. What is the capital of Canada?")).toBeInTheDocument();

    // Check Correctness badges
    expect(screen.getByText("✓ Correct")).toBeInTheDocument();
    expect(screen.getByText("✗ Incorrect")).toBeInTheDocument();

    // Check Explanations
    expect(
      screen.getByText("Tokyo has been the capital and largest city of Japan since 1868."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Ottawa was chosen by Queen Victoria as the capital of Canada."),
    ).toBeInTheDocument();
  });

  test("shows withheld message and hides answers when assignment window is still open", async () => {
    mockGetSession.mockResolvedValue({
      session_id: "session-2",
      quiz_id: "quiz-2",
      title: "Biology Exam",
      participant_name: "Sam",
      status: "submitted",
      score: 5,
      total_questions: 10,
      percentage: 50,
      auto_submitted: false,
      submitted_at: "2026-10-16T10:00:00Z",
      answers_released: false,
      release_answers_at: "2026-10-16T18:00:00Z",
      graded_answers: [],
    });

    render(<LiveQuizResultsPage sessionId="session-2" />);

    expect(await screen.findByText("Quiz result")).toBeInTheDocument();
    expect(screen.getAllByText("Pending release").length).toBe(2);
    expect(screen.getByText("Answers Withheld Until Deadline")).toBeInTheDocument();
    expect(
      screen.getByText(/detailed answers and explanations will be released after the assignment window closes/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Question Results & Explanations")).not.toBeInTheDocument();
  });
});
