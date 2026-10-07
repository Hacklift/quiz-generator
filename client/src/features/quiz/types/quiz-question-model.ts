export interface Question {
  question: string;
  options?: string[];
  correct_answer: string | Record<string, string>;
}
