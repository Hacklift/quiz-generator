import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import QuizForm from "@features/quiz/components/QuizForm";
import type { Persona, PersonaUserType } from "@shared/config/persona";

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

  test("allows query params to override teacher preset defaults", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
      preset: "class-quiz",
      difficultyLevel: "hard",
      numQuestions: "6",
      audienceType: "exam candidates",
      questionType: "short-answer",
      customInstruction: "Prioritize applied reasoning questions.",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue(
        "exam candidates",
      );
    });
    expect(screen.getByRole("button", { name: /hard/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("6")).toBeInTheDocument();
    expect(screen.getByLabelText("Short Answer")).toBeChecked();
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Prioritize applied reasoning questions.",
    );
  });

  const PERSONA_DEFAULT_CASES: Array<{
    userType: PersonaUserType;
    category: Persona["category"];
    audience: string;
    difficulty: RegExp;
    questionType: string;
  }> = [
    {
      userType: "teacher",
      category: "school",
      audience: "students",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "lecturer",
      category: "school",
      audience: "undergraduates",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "student",
      category: "school",
      audience: "students",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "parent",
      category: "school",
      audience: "children",
      difficulty: /easy/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "business",
      category: "corporate",
      audience: "employees",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "employee",
      category: "corporate",
      audience: "employees",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
    {
      userType: "hr",
      category: "corporate",
      audience: "employees",
      difficulty: /medium/i,
      questionType: "Multiple Choice",
    },
  ];

  test.each(PERSONA_DEFAULT_CASES)(
    "applies persona generation defaults for $userType",
    async ({ userType, category, audience, difficulty, questionType }) => {
      mockPersona = { category, userType };
      mockSearchParams = new URLSearchParams({
        category,
        persona: userType,
      });

      render(<QuizForm />);

      await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue(audience);
    });
    expect(screen.getByRole("button", { name: difficulty })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText(questionType)).toBeChecked();
    expect(screen.getByPlaceholderText("Add specific instruction")).not.toHaveValue("");
    },
  );

  test("applies the same defaults when persona comes from profile without query params", async () => {
    mockPersona = { category: "school", userType: "parent" };
    mockSearchParams = new URLSearchParams({
      topic: "Multiplication tables",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("children");
    });
    expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
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

  test("does not clobber manual form edits if persona changes after defaults apply", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    const { rerender } = render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("students");
    });

    fireEvent.change(screen.getByPlaceholderText("Audience"), {
      target: { value: "my custom audience" },
    });
    fireEvent.change(screen.getByDisplayValue("10"), {
      target: { value: "4" },
    });

    mockPersona = { category: "school", userType: "parent" };
    rerender(<QuizForm />);

    expect(screen.getByPlaceholderText("Audience")).toHaveValue(
      "my custom audience",
    );
    expect(screen.getByDisplayValue("4")).toBeInTheDocument();
  });

  test("ignores invalid query param overrides and falls back to persona defaults", async () => {
    mockPersona = { category: "school", userType: "parent" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "parent",
      difficultyLevel: "extreme",
      numQuestions: "many",
      questionType: "essay",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("children");
    });
    expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
  });
});

