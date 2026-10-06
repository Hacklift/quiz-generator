export interface QuizAnswerFieldProps {
  questionType: string;
  index: number;
  onAnswerChange: (index: number, answer: string | number | Record<string, string>) => void;
  options: string[];
  value?: string | number | Record<string, string>;
  disabled?: boolean;
}
