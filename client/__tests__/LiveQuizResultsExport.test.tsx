import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { LiveQuizCreatorDashboard } from "../pages/my-live-quizzes/[quizId]";
import { MyLiveQuizzesPage } from "../pages/my-live-quizzes";
import { liveQuizService } from "@features/live-quiz/api/liveQuizService";
import { usePersona } from "@features/persona/context/personaContext";

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn(), query: { quizId: "quiz-1" } }),
}));
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
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

const mockedPersona = usePersona as jest.Mock;
const mockedService = liveQuizService as jest.Mocked<typeof liveQuizService>;

describe("live quiz results export", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedService.listParticipants.mockResolvedValue([]);
    mockedService.subscribeParticipants.mockReturnValue({
      close: jest.fn(),
    } as unknown as WebSocket);
    mockedPersona.mockReturnValue({ userType: "teacher" });
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  test("teacher can request a server-generated format", async () => {
    mockedService.downloadResults.mockResolvedValue({
      blob: new Blob(["results"]),
      contentDisposition: 'attachment; filename="Class results.csv"',
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: jest.fn(() => "blob:results"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: jest.fn(),
    });

    render(<LiveQuizCreatorDashboard quizId="quiz-1" />);
    await screen.findByText("No participants yet.");
    fireEvent.change(screen.getByLabelText("Export format"), {
      target: { value: "pdf" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Export results" }));

    await waitFor(() =>
      expect(mockedService.downloadResults).toHaveBeenCalledWith("quiz-1", "pdf"),
    );
  });

  test("does not show export controls to a parent", async () => {
    mockedPersona.mockReturnValue({ userType: "parent" });
    render(<LiveQuizCreatorDashboard quizId="quiz-1" />);
    await screen.findByText("No participants yet.");
    expect(screen.queryByRole("button", { name: "Export results" })).toBeNull();
  });

  test("creator can export each quiz directly from Live Quizzes history", async () => {
    mockedService.listLiveQuizzes.mockResolvedValue([
      {
        quiz_id: "quiz-1",
        title: "Biology Session",
        status: "completed",
        participant_count: 2,
        completed_count: 2,
      },
    ]);
    mockedService.downloadResults.mockResolvedValue({
      blob: new Blob(["results"]),
      contentDisposition: 'attachment; filename="Biology Session results.csv"',
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: jest.fn(() => "blob:results"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: jest.fn(),
    });

    render(<MyLiveQuizzesPage />);
    await screen.findByText("Biology Session");
    fireEvent.click(
      screen.getByRole("button", { name: "More actions for Biology Session" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "CSV" }));

    await waitFor(() =>
      expect(mockedService.downloadResults).toHaveBeenCalledWith("quiz-1", "csv"),
    );
  });
});
