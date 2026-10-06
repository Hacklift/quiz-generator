export interface GeneratedQuizModel {
  question: string;
  options?: string[];
  correct_answer: string | Record<string, string>;
  question_type: string;
  answer: string | number | Record<string, string>;
}
