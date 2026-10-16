import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import QuizForm from "@features/quiz/components/QuizForm";
import type { Persona, PersonaUserType } from "@shared/config/persona";

const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();
let mockPersona: Persona | null = null;
let mockAppLocale = "en";
jest.mock("@features/locale/context/localeContext", () => ({
  useLocale: () => ({ locale: mockAppLocale }),
}));

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
    mockAppLocale = "en";
    sessionStorage.clear();
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

  test("quiz language is the final form section and its searchable list collapses without losing selection", () => {
    render(<QuizForm />);
    const toggle = screen.getByRole("button", {
      name: "Quiz language: English (en)",
    });
    const panel = document.getElementById(
      toggle.getAttribute("aria-controls")!,
    );
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(panel).not.toBeVisible();
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    const form = toggle.closest("form")!;
    const sections = form.querySelectorAll(":scope > section");
    expect(sections[sections.length - 1]).toContainElement(toggle);
    const provider = screen.getByLabelText("AI provider");
    expect(sections[sections.length - 2]).toContainElement(provider);
    expect(provider.closest("section")?.nextElementSibling).toBe(
      toggle.closest("section"),
    );
    const generate = screen.getByRole("button", { name: /generate quiz/i });
    expect(
      toggle.compareDocumentPosition(generate) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(panel).toBeVisible();
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "French" },
    });
    fireEvent.change(screen.getByLabelText("Quiz language"), {
      target: { value: "fr" },
    });
    expect(toggle).toHaveTextContent("Français (fr)");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(panel).not.toBeVisible();
    expect(toggle).toHaveTextContent("Français (fr)");
    fireEvent.click(toggle);
    expect(screen.getByRole("searchbox")).toHaveValue("French");
    expect(screen.getByLabelText("Quiz language")).toHaveValue("fr");
  });

  test("quiz language is independent of later app-language changes and retained in the stored quiz", async () => {
    const publicApi = require("@shared/api/publicHttp").default;
    publicApi.post.mockResolvedValue({
      data: {
        title: "Quiz français",
        content_locale: "fr",
        source: "huggingface",
        questions: [
          {
            question: "Combien font deux plus deux ?",
            answer: "Quatre",
            explanation: "Deux et deux font quatre.",
          },
        ],
      },
    });
    const view = render(<QuizForm />);
    fireEvent.click(screen.getByRole("button", { name: /^Quiz language:/ }));
    fireEvent.change(screen.getByLabelText("Search languages"), {
      target: { value: "French" },
    });
    fireEvent.change(screen.getByLabelText("Quiz language"), {
      target: { value: "fr" },
    });
    mockAppLocale = "es";
    view.rerender(<QuizForm />);
    expect(screen.getByLabelText("Quiz language")).toHaveValue("fr");
    fireEvent.change(
      screen.getByPlaceholderText("Enter the concept/context here"),
      { target: { value: "Arithmetic" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));
    await waitFor(() =>
      expect(publicApi.post).toHaveBeenCalledWith(
        "/api/get-questions",
        expect.objectContaining({
          content_locale: "fr",
          allow_fallback: false,
        }),
      ),
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalled());
    const stored = JSON.parse(sessionStorage.getItem("generated_quiz_view")!);
    expect(stored.content_locale).toBe("fr");
    expect(stored.title).toBe("Quiz français");
    expect(stored.questions[0].explanation).toBe("Deux et deux font quatre.");
  });

  test("sample fallback requires consent and is disabled for unsupported languages", () => {
    render(<QuizForm />);
    const checkbox = screen.getByRole("checkbox", {
      name: /if AI is unavailable/i,
    });
    expect(checkbox).not.toBeChecked();
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: /^Quiz language:/ }));
    fireEvent.change(screen.getByLabelText("Search languages"), {
      target: { value: "German" },
    });
    fireEvent.change(screen.getByLabelText("Quiz language"), {
      target: { value: "de" },
    });
    expect(checkbox).toBeDisabled();
    expect(checkbox).not.toBeChecked();
  });

  test.each(["huggingface", "gemini"])(
    "document generation sends its separate quiz language via %s",
    async (provider) => {
      const publicApi = require("@shared/api/publicHttp").default;
      publicApi.post.mockResolvedValue({
        data: {
          title: "Quiz español",
          content_locale: "es",
          source: "document-rag",
          source_document_type: "text",
          questions: [{ question: "Pregunta", answer: "Respuesta" }],
        },
      });
      render(<QuizForm />);
      fireEvent.change(screen.getByLabelText("AI provider"), {
        target: { value: provider },
      });
      fireEvent.click(screen.getByRole("button", { name: /^Quiz language:/ }));
      fireEvent.change(screen.getByLabelText("Search languages"), {
        target: { value: "Spanish" },
      });
      fireEvent.change(screen.getByLabelText("Quiz language"), {
        target: { value: "es" },
      });
      fireEvent.click(
        screen.getByRole("button", { name: /document or pasted text/i }),
      );
      fireEvent.click(screen.getByRole("button", { name: /paste text/i }));
      fireEvent.change(
        screen.getByPlaceholderText(
          "Paste lecture notes, textbook excerpts, or study material here.",
        ),
        { target: { value: "Some learning material." } },
      );
      fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));
      await waitFor(() => expect(publicApi.post).toHaveBeenCalled());
      const [path, payload] = publicApi.post.mock.calls[0];
      expect(path).toBe("/api/document-quizzes/generate");
      expect(payload.get("content_locale")).toBe("es");
      expect(payload.get("ai_provider")).toBe(provider);
      if (provider === "gemini") expect(payload.has("token")).toBe(false);
      expect(payload.get("allow_fallback")).toBe("false");
    },
  );

  test("Gemini generates Latin independently of app language without exposing HF tokens", async () => {
    const publicApi = require("@shared/api/publicHttp").default;
    publicApi.post.mockResolvedValue({
      data: {
        content_locale: "la",
        source: "gemini",
        title: "Exercitatio",
        questions: [
          {
            question: "Quot sunt duo et duo?",
            answer: "Quattuor",
            explanation: "Duo et duo quattuor sunt.",
          },
        ],
      },
    });
    render(<QuizForm />);
    expect(screen.getByLabelText("AI provider")).toHaveValue("huggingface");
    const tokenInput = screen.getByPlaceholderText("Enter your API token");
    fireEvent.change(tokenInput, {
      target: { value: "hf_private_test_token" },
    });
    fireEvent.change(screen.getByLabelText("AI provider"), {
      target: { value: "gemini" },
    });
    expect(
      screen.queryByPlaceholderText("Enter your API token"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Quiz language:/ }));
    fireEvent.change(screen.getByLabelText("Search languages"), {
      target: { value: "Latin" },
    });
    fireEvent.change(screen.getByLabelText("Quiz language"), {
      target: { value: "la" },
    });
    fireEvent.change(
      screen.getByPlaceholderText("Enter the concept/context here"),
      { target: { value: "Arithmetic" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));
    await waitFor(() =>
      expect(publicApi.post).toHaveBeenCalledWith(
        "/api/get-questions",
        expect.objectContaining({
          ai_provider: "gemini",
          content_locale: "la",
          token: undefined,
        }),
      ),
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalled());
    expect(mockPush.mock.calls[0][0]).not.toContain("hf_private");
    const stored = JSON.parse(sessionStorage.getItem("generated_quiz_view")!);
    expect(stored.content_locale).toBe("la");
    expect(stored.source).toBe("gemini");
  });

  test("provider billing errors explain the failure and allow a different provider", async () => {
    const publicApi = require("@shared/api/publicHttp").default;
    publicApi.post.mockRejectedValue({
      response: {
        data: { detail: { code: "billing", provider: "Hugging Face" } },
      },
    });
    render(<QuizForm />);
    fireEvent.change(
      screen.getByPlaceholderText("Enter the concept/context here"),
      { target: { value: "Arithmetic" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /generate quiz/i }));
    expect(
      await screen.findByText(/Hugging Face requires payment or credits/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("AI provider")).not.toBeDisabled();
    fireEvent.change(screen.getByLabelText("AI provider"), {
      target: { value: "gemini" },
    });
    expect(screen.getByLabelText("AI provider")).toHaveValue("gemini");
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
        screen.getByPlaceholderText("Photosynthesis — Grade 8 biology"),
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

  test("reconciles defaults when a preset is removed for the same persona", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
      preset: "class-quiz",
    });
    const { rerender } = render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Create a marking-ready in-class quiz with clear answer options and an answer key.",
    );

    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
    });
    rerender(<QuizForm />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /medium/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Use clear classroom language, include marking-friendly questions, and keep the answer key suitable for teacher review.",
    );
  });

  test("applies lecturer lecture recap preset from persona dashboard query params", async () => {
    mockPersona = { category: "school", userType: "lecturer" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "lecturer",
      preset: "lecture-recap",
    });

    render(<QuizForm />);

    expect(
      screen.getByPlaceholderText("Introduction to microeconomics"),
    ).toHaveValue("");
    expect(screen.getByPlaceholderText("Audience")).toHaveValue(
      "undergraduates",
    );
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Create a concise post-lecture recap that checks retention of the key concepts covered in the lecture.",
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
      expect(
        screen.getByRole("button", { name: difficulty }),
      ).toBeInTheDocument();
      expect(screen.getByDisplayValue("10")).toBeInTheDocument();
      expect(screen.getByLabelText(questionType)).toBeChecked();
      expect(
        screen.getByPlaceholderText("Add specific instruction"),
      ).not.toHaveValue("");
    },
  );

  test("applies the same defaults when persona comes from profile without query params", async () => {
    mockPersona = { category: "school", userType: "parent" };
    mockSearchParams = new URLSearchParams();

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("children");
    });
    expect(
      screen.getByPlaceholderText("Multiplication tables — ages 7 to 9"),
    ).toHaveValue("");
    expect(screen.getByRole("button", { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiple Choice")).toBeChecked();
  });

  test("keeps explicit non-default topic query params as the concept value", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
      topic: "Cell respiration",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Photosynthesis — Grade 8 biology"),
      ).toHaveValue("Cell respiration");
    });
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

  test("re-applies defaults when a preliminary persona resolves to the profile persona", async () => {
    mockPersona = { category: "school", userType: "parent" };
    const { rerender } = render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("children");
    });
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Use child-friendly wording, simple examples, and auto-marked questions a parent can review quickly.",
    );

    mockPersona = { category: "school", userType: "teacher" };
    rerender(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("students");
    });
    expect(screen.getByRole("button", { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Use clear classroom language, include marking-friendly questions, and keep the answer key suitable for teacher review.",
    );
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

  test("clamps excessive query param question counts to the generation maximum", async () => {
    mockPersona = { category: "school", userType: "teacher" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "teacher",
      numQuestions: "100000",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("10")).toBeInTheDocument();
    });
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

  test("applies persona custom instruction when preset query is not applicable", async () => {
    mockPersona = { category: "school", userType: "student" };
    mockSearchParams = new URLSearchParams({
      category: "school",
      persona: "student",
      preset: "class-quiz",
    });

    render(<QuizForm />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Audience")).toHaveValue("students");
    });
    expect(screen.getByPlaceholderText("Add specific instruction")).toHaveValue(
      "Create self-practice questions with immediate learning value and wording suited to exam revision.",
    );
  });
});
