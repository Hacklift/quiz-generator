import axios from "axios";
import { TokenService } from "./tokenService";

export async function saveQuizToHistory(
  meta: {
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
    quiz_name: `${meta.question_type} Quiz`,
    question_type: meta.question_type,
    num_questions: meta.num_questions,
    difficulty_level: meta.difficulty_level,
    profession: meta.profession,
    audience_type: meta.audience_type,
    custom_instruction: meta.custom_instruction,
    questions: formattedQuestions,
  };

  console.log("🔵 SAVE HISTORY PAYLOAD:", payload);

  return axios.post(
    `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/save-quiz`,
    payload,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    },
  );
}
