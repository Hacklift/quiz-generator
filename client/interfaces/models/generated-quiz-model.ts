export interface GeneratedQuizModel {
  question: string;
  options?: string[];
  correct_answer: string; // ✅ Add this line
  question_type: string;
  answer: string | number;
}
