import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";
import { saveQuiz } from "@features/saved-quizzes/api/savedQuizApi";
import { api } from "@shared/api/http";

jest.mock("@shared/api/http", () => ({
  api: { post: jest.fn().mockResolvedValue({ data: {} }) },
}));
jest.mock("@shared/auth/tokenService", () => ({
  TokenService: { getAccessToken: () => "test-token" },
}));

const question = {
  question: "Un carré a quatre côtés.",
  options: ["Vrai", "Faux"],
  answer: "Vrai",
  explanation: "Un carré possède quatre côtés égaux.",
  correct_boolean: true,
  question_type: "true-false",
};
beforeEach(() => jest.clearAllMocks());

test("history creation without an ID carries the quiz language, generated title and answer metadata", async () => {
  await saveQuizToHistory(
    {
      content_locale: "fr",
      title: "Quiz français",
      description: "Description française",
      question_type: "true-false",
      num_questions: 1,
      difficulty_level: "easy",
      profession: "English topic",
      audience_type: "students",
      custom_instruction: "",
    },
    [question],
  );
  expect(api.post).toHaveBeenCalledWith(
    "/api/save-quiz",
    expect.objectContaining({
      content_locale: "fr",
      quiz_name: "Quiz français",
      description: "Description française",
      questions: [expect.objectContaining(question)],
    }),
  );
});

test("saving a quiz without an ID preserves its language and answers", async () => {
  await saveQuiz(
    "Quiz français",
    "true-false",
    [question],
    "test-token",
    undefined,
    "fr",
    "Description française",
    true,
  );
  expect(api.post).toHaveBeenCalledWith(
    "/api/saved-quizzes/",
    expect.objectContaining({
      content_locale: "fr",
      is_sample: true,
      description: "Description française",
      questions: [expect.objectContaining(question)],
    }),
    expect.any(Object),
  );
});
