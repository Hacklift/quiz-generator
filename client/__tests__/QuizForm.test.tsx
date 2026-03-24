import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import QuizForm from "../components/home/QuizForm";

const push = jest.fn();
const mockApiGet = jest.fn();
const mockApiPost = jest.fn();

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
    expect(push).not.toHaveBeenCalled();
  });

  test("submits quiz generation and routes to quiz display", async () => {
    render(<QuizForm />);

    fireEvent.change(
      screen.getByPlaceholderText("Enter the concept/context here"),
      { target: { value: "Physics" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));

    await waitFor(() => {
      expect(push).toHaveBeenCalledWith(
        expect.stringContaining(
          "/quiz_display?questionType=multichoice&numQuestions=1&profession=Physics",
        ),
      );
    });
  });
});
