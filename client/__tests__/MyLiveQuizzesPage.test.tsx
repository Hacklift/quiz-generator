import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MyLiveQuizzesPage } from "@features/live-quiz/pages/MyLiveQuizzesPage";
import { LiveQuizCreatorDashboard } from "@features/live-quiz/pages/LiveQuizCreatorDashboardPage";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";
import { usePersona } from "@features/persona/context/personaContext";

const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push: mockPush, query: {}, isReady: true }),
}));
jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => children,
}));
jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => null,
}));
jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => null,
}));
jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: jest.fn(),
}));
jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: {
    listParticipants: jest.fn(),
    subscribeParticipants: jest.fn(),
    downloadResults: jest.fn(),
    listLiveQuizzes: jest.fn(),
    createAccessCode: jest.fn(),
  },
}));

/** Value of a summary stat, read from its <dt>/<dd> pair. */
const statValue = (label: string) => {
  const terms = screen.getAllByRole("term").map((term) => term.textContent);
  const values = screen.getAllByRole("definition");
  // Labels may carry a short mobile variant first, e.g. "Open codesOpen access codes".
  return values[terms.findIndex((term) => term?.endsWith(label))]?.textContent;
};

const mockedService = liveQuizService as jest.Mocked<typeof liveQuizService>;
const future = new Date(Date.now() + 60 * 60 * 1000).toISOString();
const past = new Date(Date.now() - 60 * 60 * 1000).toISOString();

describe("MyLiveQuizzesPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedService.listLiveQuizzes.mockResolvedValue([
      {
        quiz_id: "quiz-open",
        title: "Biology Session",
        status: "active",
        access_code: "BIO123",
        access_code_expires_at: future,
        participant_count: 3,
        completed_count: 1,
        average_score: 70,
      },
      {
        quiz_id: "quiz-expired",
        title: "Chemistry Session",
        status: "expired",
        access_code: "CHEM99",
        access_code_expires_at: past,
        participant_count: 2,
        completed_count: 2,
      },
    ]);
  });

  test("shows summary totals and each quiz's access code", async () => {
    render(<MyLiveQuizzesPage />);

    await screen.findByText("Biology Session");
    expect(screen.getByText("BIO123")).toBeInTheDocument();
    expect(statValue("Open access codes")).toBe("1");
    expect(statValue("Participants")).toBe("5");
    // Only the quiz with an expired code offers a replacement code.
    expect(screen.getAllByRole("button", { name: "New access code" })).toHaveLength(1);
  });

  test("generates a new access code for an expired quiz", async () => {
    mockedService.createAccessCode.mockResolvedValue({
      access_code: "NEW456",
    } as any);

    render(<MyLiveQuizzesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "New access code" }));

    expect(screen.getByRole("dialog")).toHaveTextContent("Chemistry Session");
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() =>
      expect(mockedService.createAccessCode).toHaveBeenCalledWith(
        expect.objectContaining({ quizId: "quiz-expired" }),
      ),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(mockedService.listLiveQuizzes).toHaveBeenCalledTimes(2);
  });

  test("closes the export menu on Escape", async () => {
    render(<MyLiveQuizzesPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: "More actions for Biology Session" }),
    );
    expect(screen.getByRole("button", { name: "CSV" })).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("button", { name: "CSV" })).not.toBeInTheDocument();
  });

  test("closes the export menu on an outside click", async () => {
    render(<MyLiveQuizzesPage />);
    fireEvent.click(
      await screen.findByRole("button", { name: "More actions for Biology Session" }),
    );
    expect(screen.getByRole("button", { name: "CSV" })).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(screen.queryByRole("button", { name: "CSV" })).not.toBeInTheDocument();
  });

  test("shows an empty state when there are no live quizzes", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([]);
    render(<MyLiveQuizzesPage />);

    expect(await screen.findByText("No live quizzes yet.")).toBeInTheDocument();
  });
});

describe("LiveQuizCreatorDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (usePersona as jest.Mock).mockReturnValue({ userType: "teacher" });
    mockedService.subscribeParticipants.mockReturnValue({
      close: jest.fn(),
    } as unknown as WebSocket);
    mockedService.listParticipants.mockResolvedValue([
      {
        session_id: "s-1",
        participant_name: "Ada",
        participant_email: "ada@example.com",
        score: 8,
        total_questions: 10,
        percentage: 80,
        progress: 10,
        submitted_at: past,
        status: "submitted",
        auto_submitted: false,
      },
      {
        session_id: "s-2",
        participant_name: "Ben",
        total_questions: 10,
        progress: 4,
        current_question_number: 5,
        status: "in_progress",
        auto_submitted: false,
      },
    ]);
  });

  test("renders participant stats, progress and a link to submitted answers", async () => {
    render(<LiveQuizCreatorDashboard quizId="quiz-1" />);

    await screen.findAllByText("Ada");
    expect(statValue("Average score")).toBe("80.0%");
    expect(screen.getByText("On question 5 of 10")).toBeInTheDocument();

    // Rendered twice in jsdom: mobile card and desktop table.
    const [viewAnswers] = screen.getAllByRole("button", { name: "View answers" });
    fireEvent.click(viewAnswers);
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes/quiz-1/attempts/s-1");
  });

  test("shows a way back to the list when the quiz is not found", async () => {
    mockedService.listParticipants.mockRejectedValue({ response: { status: 404 } });
    render(<LiveQuizCreatorDashboard quizId="missing" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Quiz not found.");
    fireEvent.click(screen.getByRole("button", { name: "All live quizzes" }));
    expect(mockPush).toHaveBeenCalledWith("/my-live-quizzes");
  });
});
