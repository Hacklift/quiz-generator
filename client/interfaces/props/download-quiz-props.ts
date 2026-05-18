export interface DownloadQuizProps {
  question_type: string;
  numQuestion: number;
  quizId?: string;
  quizData?: Array<{
    question: string;
    options?: string[];
    answer?: string | number;
    correct_answer?: string;
    question_type?: string;
  }>;
  title?: string;
  description?: string;
}
