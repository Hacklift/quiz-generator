import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import QuizDisplayPage from "../pages/quiz_display";

const mockSearchParamsGet = jest.fn();
const mockPublicPost = jest.fn();
const mockApiGet = jest.fn();
const mockSaveQuizToHistory = jest.fn();
const mockHasTokens = jest.fn();

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({ get: (key: string) => mockSearchParamsGet(key) }),
}));

jest.mock("../components/home", () => ({
  CheckButton: ({ onClick }: { onClick: () => void }) => (
    <button onClick={onClick}>Check</button>
  ),
  NewQuizButton: () => <button>New Quiz</button>,
  QuizAnswerField: () => <div>Answer Field</div>,
  DownloadQuizButton: () => <button>Download</button>,
  NavBar: () => <div data-testid="navbar" />,
  Footer: () => <div data-testid="footer" />,
  ShareButton: () => <button>Share</button>,
  SaveQuizButton: () => <button>Save</button>,
}));

jest.mock("../lib/functions/saveQuizToHistory", () => ({
  saveQuizToHistory: (...args: unknown[]) => mockSaveQuizToHistory(...args),
}));

jest.mock("../lib/functions/auth", () => ({
  api: { get: (...args: unknown[]) => mockApiGet(...args) },
}));

jest.mock("../lib/functions/publicApi", () => ({
  __esModule: true,
  default: { post: (...args: unknown[]) => mockPublicPost(...args) },
}));

jest.mock("../lib/functions/tokenService", () => ({
  TokenService: { hasTokens: (...args: unknown[]) => mockHasTokens(...args) },
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

describe("QuizDisplayPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSearchParamsGet.mockImplementation((key: string) => {
      const map: Record<string, string | null> = {
        id: null,
        questionType: "multichoice",
        numQuestions: "1",
        profession: "science",
        difficultyLevel: "easy",
        audienceType: "students",
        customInstruction: "",
      };
      return map[key] ?? null;
    });

    mockPublicPost.mockResolvedValue({
      data: {
        questions: [
          {
            question: "What is the capital of France?",
            options: ["Paris", "Rome"],
            answer: "Paris",
            question_type: "multichoice",
          },
        ],
      },
    });
    mockHasTokens.mockReturnValue(true);
    mockSaveQuizToHistory.mockResolvedValue({});
  });

  test("loads generated quiz and saves history for authenticated users", async () => {
    render(<QuizDisplayPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/What is the capital of France\?/i),
      ).toBeInTheDocument();
    });

    expect(mockPublicPost).toHaveBeenCalledWith(
      "/api/get-questions",
      expect.any(Object),
    );
    expect(mockSaveQuizToHistory).toHaveBeenCalled();
  });
});
