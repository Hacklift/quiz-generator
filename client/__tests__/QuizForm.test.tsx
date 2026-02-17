import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import QuizForm from "../components/home/QuizForm";

const mockPost = jest.fn();
const mockGet = jest.fn();
const push = jest.fn();

jest.mock("axios", () => ({
  post: (...args: any[]) => mockPost(...args),
  get: (...args: any[]) => mockGet(...args),
}));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const mockUseAuth = jest.fn();

jest.mock("../contexts/authContext", () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock("../lib/functions/tokenService", () => ({
  TokenService: { getAccessToken: jest.fn() },
}));

import { TokenService } from "../lib/functions/tokenService";

describe("QuizForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: null });
  });

  test("calls generate endpoint with correct payload", async () => {
    mockPost.mockResolvedValue({ data: { questions: [], source: "mock" } });

    render(<QuizForm />);

    fireEvent.change(screen.getByPlaceholderText(/Enter the concept/i), {
      target: { value: "Biology" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Audience/i), {
      target: { value: "Students" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate Quiz/i }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining("/api/get-questions"),
        expect.objectContaining({
          profession: "Biology",
          audience_type: "Students",
          question_type: "multichoice",
          difficulty_level: "easy",
        }),
        expect.anything(),
      );
    });
  });

  test("sends token when provided", async () => {
    (TokenService.getAccessToken as jest.Mock).mockReturnValue("access");

    mockUseAuth.mockReturnValue({ user: { id: "1" } });

    mockPost
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce({ data: { questions: [], source: "mock" } });

    render(<QuizForm />);

    fireEvent.change(screen.getByPlaceholderText(/Enter the concept/i), {
      target: { value: "Math" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Enter your API token/i), {
      target: { value: "token123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Generate Quiz/i }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        expect.stringContaining("/api/user/token"),
        { token: "token123" },
        expect.objectContaining({
          headers: { Authorization: "Bearer access" },
          withCredentials: true,
        }),
      );
    });
  });
});
