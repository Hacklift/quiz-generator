import { api } from "@shared/api/http";
import { TokenService } from "@shared/auth/tokenService";

export async function saveQuizToHistory(
  meta: {
    quiz_id?: string;
    content_locale?: string;
    title?: string;
    description?: string;
    is_sample?: boolean;
    question_type: string;
    num_questions: number;
    difficulty_level: string;
    profession: string;
    audience_type: string;
    custom_instruction: string;
  },
  questions: any[],
) {
  const token = TokenService.getAccessToken();

  const formattedQuestions = questions.map((q: any) => ({
    question: q.question,
    options: q.options || null,
    answer: q.answer || q.correct_answer,
    explanation: q.explanation,
    correct_option_index: q.correct_option_index,
    correct_boolean: q.correct_boolean,
    question_type: q.question_type,
  }));

  const payload = {
    quiz_id: meta.quiz_id,
    quiz_name: meta.title || meta.profession || `${meta.question_type} Quiz`,
    content_locale: meta.content_locale || "en",
    description: meta.description,
    is_sample: meta.is_sample || false,
    question_type: meta.question_type,
    num_questions: meta.num_questions,
    difficulty_level: meta.difficulty_level,
    profession: meta.profession,
    audience_type: meta.audience_type,
    custom_instruction: meta.custom_instruction,
    questions: formattedQuestions,
  };

  if (!token) {
    throw new Error("No access token found");
  }

  return api.post("/api/save-quiz", payload);
}
