import axios from "axios";
import { GeneratedQuizModel } from "../../interfaces/models";

export const saveQuizToHistory = async (
  userId: string,
  questionType: string,
  questions: GeneratedQuizModel[],
) => {
  try {
    if (!Array.isArray(questions)) {
      console.error("❌ Expected questions to be an array but got:", questions);
      return;
    }

    const formattedQuestions = questions.map((q) => ({
      question: q.question,
      options: Array.isArray(q.options) ? q.options : undefined,
      answer: q.correct_answer,
      question_type: q.question_type,
    }));

    const payload = {
      user_id: userId,
      question_type: questionType,
      questions: formattedQuestions,
      //created_at: new Date().toISOString(),
    };

    console.log("📦 Sending to API:", payload);

    await axios.post(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/save-quiz`,
      payload,
    );
  } catch (error) {
    console.error("❌ Failed to save quiz history:", error);
  }
};
