import { Dispatch, SetStateAction } from "react";

export interface QuizGenerationSectionProps {
  profession: string;
  setProfession: Dispatch<SetStateAction<string>>;
  audienceType: string;
  setAudienceType: Dispatch<SetStateAction<string>>;
  customInstruction: string;
  setCustomInstruction: Dispatch<SetStateAction<string>>;
  numQuestions: number;
  setNumQuestions: Dispatch<SetStateAction<number>>;
  questionType: string;
  setQuestionType: Dispatch<SetStateAction<string>>;
  difficultyLevel: string;
  setDifficultyLevel: Dispatch<SetStateAction<string>>;
}
