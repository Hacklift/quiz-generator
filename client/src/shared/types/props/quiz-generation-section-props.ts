import { Dispatch, SetStateAction } from "react";

export interface QuizGenerationSectionProps {
  generationMode: "document" | "topic";
  setGenerationMode: Dispatch<SetStateAction<"document" | "topic">>;
  profession: string;
  setProfession: Dispatch<SetStateAction<string>>;
  documentTitle: string;
  setDocumentTitle: Dispatch<SetStateAction<string>>;
  documentInputMode: "paste" | "upload";
  setDocumentInputMode: Dispatch<SetStateAction<"paste" | "upload">>;
  documentText: string;
  setDocumentText: Dispatch<SetStateAction<string>>;
  documentFileName: string;
  onDocumentFileChange: (file: File | null) => void;
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
