import axios from "axios";

const API_URL = `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/saved-quizzes`;
const DEFAULT_USER_ID = "dummy-user-123"; // fallback until authentication is ready

// ✅ Save a quiz
export const saveQuiz = async (
  title: string,
  questionType: string,
  questions: any[],
  userId: string = DEFAULT_USER_ID,
) => {
  if (!Array.isArray(questions) || questions.length === 0) {
    throw new Error("No questions provided for saving.");
  }

  // ✅ Format questions to match backend model
  const formattedQuestions = questions.map((q) => ({
    question: q.question || "",
    options: q.options || null,
    question_type: q.question_type || questionType,
  }));

  // ✅ Build payload
  const payload = {
    user_id: userId,
    title,
    question_type: questionType,
    questions: formattedQuestions,
  };

  console.log("📤 Saving quiz payload:", payload);

  // ✅ Send to backend
  const res = await axios.post(`${API_URL}/`, payload);
  return res.data;
};

// ✅ Get all saved quizzes
export const getSavedQuizzes = async () => {
  const res = await axios.get(`${API_URL}/`);
  return res.data;
};

// ✅ Delete a saved quiz
export const deleteSavedQuiz = async (quizId: string) => {
  const res = await axios.delete(`${API_URL}/${quizId}`);
  return res.data;
};
