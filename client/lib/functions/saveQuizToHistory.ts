import { TokenService } from "./tokenService";
import { api } from "./auth";

export async function saveQuizToHistory(
  meta: {
    quiz_id?: string;
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
    question_type: q.question_type,
  }));

  const payload = {
    quiz_id: meta.quiz_id,
    quiz_name: `${meta.question_type} Quiz`,
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
