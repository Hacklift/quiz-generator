import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import QuizForm from "@features/quiz/components/QuizForm";
import type { Persona } from "@shared/config/persona";

const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();
let mockPersona: Persona | null = null;

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => mockSearchParams,
}));

jest.mock("@features/auth/context/authContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
  }),
}));

jest.mock("@shared/api/http", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

jest.mock("@shared/api/publicHttp", () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock("@features/persona/context/personaContext", () => ({
  usePersona: () => ({
    persona: mockPersona,
    isLoading: false,
  }),
}));

jest.mock("@features/persona/components/PersonaBadge", () => ({
  __esModule: true,
  default: () => <div>Persona badge</div>,
}));

describe("QuizForm", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockSearchParams = new URLSearchParams();
    mockPersona = null;
    const publicApi = require("@shared/api/publicHttp").default;
    publicApi.post.mockReset();
  });

  test("renders the quiz form with initial state", () => {
    render(<QuizForm />);

    expect(
      screen.getByPlaceholderText("Enter the concept/context here"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /generate quiz/i }),
    ).toBeInTheDocument();
  });

  test("updates question input on change", () => {
    render(<QuizForm />);

    const input = screen.getByPlaceholderText("Enter the concept/context here");
    fireEvent.change(input, {
      target: { value: "What is your favorite color?" },
    });

    expect(input).toHaveValue("What is your favorite color?");
  });

  test("generates quiz and redirects to quiz display", async () => {
    const publicApi = require("@shared/api/publicHttp").default;
    publicApi.post.mockResolvedValue({
      data: {
        quiz_id: "quiz-1",
        questions: [
          {
            question: "What is your favorite color?",
            options: ["Blue", "Green", "Red", "Yellow"],
            answer: "Blue",
          },
        ],
      },
    });

    render(<QuizForm />);

    const input = screen.getByPlaceholderText("Enter the concept/context here");
    fireEvent.change(input, {
      target: { value: "What is your favorite color?" },
    });

    const generateButton = screen.getByRole("button", {
      name: /generate quiz/i,
    });
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        expect.stringContaining("/quiz_display?"),
      );
    });
  });

  test("applies teacher class quiz preset from persona dashboard query params", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
      preset: "class-quiz",
      topic: "Photosynthesis",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Enter the concept/context here"),
      ).toHaveValue("Photosynthesis");
    });
    expect(screen.getByPlaceholderText("Audience")).toHaveValue("students");
    expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Create a marking-ready in-class quiz with clear answer options and an answer key.",
    );
  });

  test("applies persona generation defaults for parent role (easy, children, 10 questions)", async () => {
    mockPersona = { category: "school", userType: "parent" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "parent",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("children");
    });
    expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
  });

  test("applies persona generation defaults for lecturer role (medium, undergraduates, 10 questions)", async () => {
    mockPersona = { category: "school", userType: "lecturer" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "lecturer",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue(
        "undergraduates",
      );
    });
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
  });

  test("applies persona generation defaults for business corporate role (employees)", async () => {
    mockPersona = { category: "corporate", userType: "business" };
    mockSearchParams = new URLSearchParams({
      category: "corporate",
      persona: "business",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("employees");
    });
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
  });

  test("allows query params to override persona defaults", async () => {
    mockPersona = { category: "school", userType: "parent" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "parent",
      difficultyLevel: "hard",
      numQuestions: "5",
      audienceType: "toddlers",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("toddlers");
    });
    expect(screen.getByRole("button", { name: /hard/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("5")).toBeInTheDocument();
  });
});

