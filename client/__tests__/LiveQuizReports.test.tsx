import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import toast from "react-hot-toast";
import LiveQuizCreatorDashboardPage from "../pages/my-live-quizzes/[quizId]/index";
import MyLiveQuizzesPage from "../pages/my-live-quizzes";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";

const push = jest.fn();

jest.mock("next/router", () => ({
  useRouter: () => ({ push, query: { quizId: "quiz-1" } }),
}));

jest.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

jest.mock("@features/auth/components/RequireAuth", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock("@features/quiz/components/NavBar", () => ({
  __esModule: true,
  default: () => <nav />,
}));

jest.mock("@features/quiz/components/Footer", () => ({
  __esModule: true,
  default: () => <footer />,
}));

jest.mock("@features/live-quiz/api/liveQuizService", () => ({
  liveQuizService: {
    listParticipants: jest.fn(),
    downloadCompletionReport: jest.fn(),
    listLiveQuizzes: jest.fn(),
    createAccessCode: jest.fn(),
    getLatestRun: jest.fn(),
    subscribeParticipants: jest.fn(() => null),
  },
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

const mockedService = liveQuizService as jest.Mocked<typeof liveQuizService>;

describe("live quiz completion reports", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedService.listParticipants.mockResolvedValue([]);
    mockedService.getLatestRun.mockRejectedValue({ response: { status: 404 } });
  });

  test("shows a specific message when no reportable run exists", async () => {
    mockedService.downloadCompletionReport.mockRejectedValue({ response: { status: 404 } });
    render(<LiveQuizCreatorDashboardPage />);

    await screen.findByRole("button", { name: /export compliance record/i });
    fireEvent.click(screen.getByRole("button", { name: /export compliance record/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        "Create an access code before exporting a completion report.",
      );
    });
  });

  test("shows a generic error when report download fails unexpectedly", async () => {
    mockedService.downloadCompletionReport.mockRejectedValue(new Error("network"));
    render(<LiveQuizCreatorDashboardPage />);

    await screen.findByRole("button", { name: /export compliance record/i });
    fireEvent.click(screen.getByRole("button", { name: /export compliance record/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        "Could not download the completion report.",
      );
    });
  });

  test("allows the passing threshold to be configured when creating a run", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([
      {
        quiz_id: "quiz-1",
        title: "Safety training",
        status: "expired",
        participant_count: 0,
        completed_count: 0,
        access_code: null,
      },
    ]);
    render(<MyLiveQuizzesPage />);

    await screen.findByText("Safety training");
    fireEvent.click(screen.getByRole("button", { name: /generate access code/i }));

    const threshold = screen.getByLabelText(/passing threshold/i) as HTMLInputElement;
    expect(threshold.value).toBe("80");
    fireEvent.change(threshold, { target: { value: "70" } });
    expect(threshold.value).toBe("70");
  });

  test("loads the persisted threshold for the latest run", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([
      { quiz_id: "quiz-1", title: "Safety training", status: "expired", participant_count: 0, completed_count: 0, access_code: null },
    ]);
    mockedService.getLatestRun.mockResolvedValue({ run_id: "run-1", passing_threshold_percentage: 70 });
    render(<MyLiveQuizzesPage />);

    await screen.findByText("Safety training");
    fireEvent.click(screen.getByRole("button", { name: /generate access code/i }));

    await waitFor(() => {
      expect((screen.getByLabelText(/passing threshold/i) as HTMLInputElement).value).toBe("70");
    });
  });

  test("keeps the default threshold when no previous run exists", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([
      { quiz_id: "quiz-1", title: "Safety training", status: "expired", participant_count: 0, completed_count: 0, access_code: null },
    ]);
    render(<MyLiveQuizzesPage />);

    await screen.findByText("Safety training");
    fireEvent.click(screen.getByRole("button", { name: /generate access code/i }));

    await waitFor(() => {
      expect((screen.getByLabelText(/passing threshold/i) as HTMLInputElement).value).toBe("80");
    });
  });

  test("explains a stale-run threshold conflict", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([
      { quiz_id: "quiz-1", title: "Safety training", status: "expired", participant_count: 0, completed_count: 0, access_code: null },
    ]);
    mockedService.createAccessCode.mockRejectedValue({ response: { status: 409 } });
    render(<MyLiveQuizzesPage />);

    await screen.findByText("Safety training");
    fireEvent.click(screen.getByRole("button", { name: /generate access code/i }));
    await screen.findByRole("button", { name: "Generate" });
    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        "This live quiz run already has a different passing threshold. Refresh the run details and try again.",
      );
    });
  });
});
