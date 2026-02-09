import React from "react";
import { render, waitFor } from "@testing-library/react";
import QuizDisplayPage from "../pages/quiz_display/index";
import toast from "react-hot-toast";

const mockGet = jest.fn();
const mockPost = jest.fn();
const mockSearchParams = { get: jest.fn() };

jest.mock("axios", () => ({
  get: (...args: any[]) => mockGet(...args),
  post: (...args: any[]) => mockPost(...args),
  create: () => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  }),
}));

jest.mock("react-hot-toast", () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

jest.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  usePathname: () => "/quiz_display",
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({ user: { id: "1" } }),
}));

jest.mock("../lib/functions/tokenService", () => ({
  TokenService: { getAccessToken: jest.fn(() => "token") },
}));

describe("QuizDisplayPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("loads saved quiz from API when id query present", async () => {
    mockSearchParams.get.mockImplementation((key: string) =>
      key === "id" ? "quiz1" : null,
    );

    mockGet.mockResolvedValue({
      data: {
        questions: [{ question: "Q1", answer: "A" }],
      },
    });

    render(<QuizDisplayPage />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining("/api/saved-quizzes/quiz1"),
        expect.anything(),
      );
    });
  });

  test("loads generated quiz when no id", async () => {
    mockSearchParams.get.mockReturnValue(null);

    mockPost.mockResolvedValue({
      data: { questions: [{ question: "Q1", answer: "A" }] },
    });

    render(<QuizDisplayPage />);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining("/api/get-questions"),
        expect.any(Object),
      );
    });
  });

  test("handles AI down response", async () => {
    mockSearchParams.get.mockReturnValue(null);

    mockPost.mockResolvedValue({
      data: {
        ai_down: true,
        notification_message: "AI down",
        questions: [{ question: "Q1", answer: "A" }],
      },
    });

    render(<QuizDisplayPage />);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("AI down", expect.any(Object));
    });
  });

  test("handles error response", async () => {
    mockSearchParams.get.mockReturnValue(null);

    mockPost.mockRejectedValue(new Error("Failed"));

    render(<QuizDisplayPage />);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });
});
