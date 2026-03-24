import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import QuizForm from "../components/home/QuizForm";

const push = jest.fn();
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
const mockPublicPost = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

jest.mock("../contexts/authContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
  }),
}));

jest.mock("../lib/functions/auth", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

jest.mock("../lib/functions/publicApi", () => ({
  __esModule: true,
  default: { post: (...args: unknown[]) => mockPublicPost(...args) },
}));

describe("QuizForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test("renders the current quiz form", () => {
    render(<QuizForm />);

    expect(
      screen.getByPlaceholderText("Enter the concept/context here"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generate quiz/i }),
    ).toBeInTheDocument();
  });

  test("updates the concept field", () => {
    render(<QuizForm />);

    const input = screen.getByPlaceholderText("Enter the concept/context here");
    fireEvent.change(input, { target: { value: "World History" } });

    expect(input).toHaveValue("World History");
  });

  test("shows validation when required concept is missing", async () => {
    render(<QuizForm />);

    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));

    expect(
      await screen.findByText(/please enter a profession or topic/i),
    ).toBeInTheDocument();
    expect(mockPublicPost).not.toHaveBeenCalled();
  });

  test("submits quiz generation and routes to quiz display", async () => {
    mockPublicPost.mockResolvedValue({ data: { source: "mock" } });

    render(<QuizForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Enter the concept/context here"),
      { target: { value: "Physics" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));

    await waitFor(() => {
      expect(mockPublicPost).toHaveBeenCalledWith(
        "/api/get-questions",
        expect.objectContaining({
          profession: "Physics",
          question_type: "multichoice",
          num_questions: 1,
        }),
        expect.any(Object),
      );
    });
    expect(push).toHaveBeenCalledWith(
      expect.stringContaining("/quiz_display?"),
    );
  });
});
