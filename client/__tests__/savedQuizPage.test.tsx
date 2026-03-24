import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SavedQuizzesPage from "../pages/saved_quiz";

const push = jest.fn();
const mockGetSavedQuizzes = jest.fn();
const mockDeleteSavedQuiz = jest.fn();
const mockGetUserFolders = jest.fn();
const mockCreateFolder = jest.fn();
const mockAddQuizToFolder = jest.fn();
const mockUseAuth = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../lib/functions/savedQuiz", () => ({
  getSavedQuizzes: (...args: unknown[]) => mockGetSavedQuizzes(...args),
  deleteSavedQuiz: (...args: unknown[]) => mockDeleteSavedQuiz(...args),
}));

jest.mock("../lib/functions/folders", () => ({
  getUserFolders: (...args: unknown[]) => mockGetUserFolders(...args),
  createFolder: (...args: unknown[]) => mockCreateFolder(...args),
  addQuizToFolder: (...args: unknown[]) => mockAddQuizToFolder(...args),
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

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

describe("SavedQuizzesPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    mockUseAuth.mockReturnValue({
      token: "access-token",
      isAuthenticated: true,
    });
  });

  test("renders empty state when no saved quizzes exist", async () => {
    mockGetSavedQuizzes.mockResolvedValue([]);

    render(<SavedQuizzesPage />);

    await waitFor(() => {
      expect(
        screen.getByText("You haven’t saved any quizzes yet."),
      ).toBeInTheDocument();
    });
  });

  test("renders populated saved quizzes and views a selected quiz", async () => {
    mockGetSavedQuizzes.mockResolvedValue([
      {
        _id: "quiz-1",
        title: "Physics Basics",
        created_at: new Date().toISOString(),
        questions: [{ question: "What is force?", options: ["Push", "Pull"] }],
      },
    ]);

    render(<SavedQuizzesPage />);

    await waitFor(() => {
      expect(screen.getByText("Physics Basics")).toBeInTheDocument();
      expect(screen.getByText("1. What is force?")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /view quiz/i }));

    expect(
      JSON.parse(localStorage.getItem("saved_quiz_view") || "{}"),
    ).toMatchObject({
      _id: "quiz-1",
      title: "Physics Basics",
    });
    expect(push).toHaveBeenCalledWith("/quiz_display?id=quiz-1");
  });
});
