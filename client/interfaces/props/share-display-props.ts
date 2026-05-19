import { Quiz } from "../models";

export interface DisplayQuizProps {
  quiz: Quiz | null;
}

export interface SharePageProps {
  quiz: Quiz | null;
  notFoundQuiz?: boolean;
}
