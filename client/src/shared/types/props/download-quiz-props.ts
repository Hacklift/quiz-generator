export interface DownloadQuizProps {
  question_type: string;
  numQuestion: number;
  quizId?: string;
  contentLocale?: string;
  quizData?: Array<{
    question: string;
    options?: string[];
    answer?: string | number;
    correct_answer?: string;
    explanation?: string;
    question_type?: string;
  }>;
  title?: string;
  description?: string;
}
