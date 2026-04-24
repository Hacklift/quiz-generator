import { api } from "./auth";

const API_URL = "/api/saved-quizzes";

export const saveQuiz = async (
  title: string,
  questionType: string,
  questions: any[],
  token: string,
  quizId?: string,
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
    quiz_id: quizId,
    question_type: questionType,
    questions: formattedQuestions,
  };

  const res = await api.post(`${API_URL}/`, payload, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return res.data;
};

export const getSavedQuizzes = async (token: string) => {
  const res = await api.get(`${API_URL}/`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return res.data;
};

export const deleteSavedQuiz = async (quizId: string, token: string) => {
  const res = await api.delete(`${API_URL}/${quizId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return res.data;
};

export const duplicateSavedQuiz = async (quizId: string, token: string) => {
  const res = await api.post(
    `${API_URL}/${quizId}/duplicate`,
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  return res.data;
};

export const renameSavedQuiz = async (
  quizId: string,
  title: string,
  token: string,
) => {
  const res = await api.patch(
    `${API_URL}/${quizId}/rename`,
    { title },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  return res.data;
};
