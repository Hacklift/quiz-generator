import { api } from "./auth";

const API_URL = "/api/saved-quizzes";

export const saveQuiz = async (
  title: string,
  questionType: string,
  questions: any[],
) => {
  if (!Array.isArray(questions) || questions.length === 0) {
    throw new Error("No questions provided for saving.");
  }

  const formattedQuestions = questions.map((q) => ({
    question: q.question || "",
    options: q.options || null,
    question_type: q.question_type || questionType,
  }));

  const payload = {
    title,
    question_type: questionType,
    questions: formattedQuestions,
  };

  const res = await api.post(`${API_URL}/`, payload);

  return res.data;
};

export const getSavedQuizzes = async () => {
  const res = await api.get(`${API_URL}/`);
  return res.data;
};

export const deleteSavedQuiz = async (quizId: string) => {
  const res = await api.delete(`${API_URL}/${quizId}`);
  return res.data;
};
