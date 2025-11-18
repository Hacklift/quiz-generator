"use client";

import { useState } from "react";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import { useAuth } from "../../contexts/authContext";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function QuizForm() {
  const [profession, setProfession] = useState("");
  const [audienceType, setAudienceType] = useState("");
  const [customInstruction, setCustomInstruction] = useState("");
  const [numQuestions, setNumQuestions] = useState(1);
  const [questionType, setQuestionType] = useState("multichoice");
  const [difficultyLevel, setDifficultyLevel] = useState("easy");
  const previousToken =
    typeof window !== "undefined"
      ? localStorage.getItem("user_api_token") || undefined
      : undefined;
  const [token, setToken] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { user } = useAuth();

  const handleGenerateQuiz = async () => {
    if (!profession) {
      setErrorMessage("Please enter a profession or topic for your quiz.");
      return;
    }

    if (!questionType) {
      setErrorMessage("Please select a question type.");
      return;
    }

    if (!numQuestions || numQuestions <= 0) {
      setErrorMessage("Please enter a valid number of questions.");
      return;
    }

    setErrorMessage("");
    setLoading(true);

    try {
      if (!user && token.trim()) {
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/token`,
          { token },
        );
      }

      const { data } = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/get-questions`,
        {
          profession,
          audience_type: audienceType,
          custom_instruction: customInstruction,
          num_questions: numQuestions,
          question_type: questionType,
          difficulty_level: difficultyLevel,
          token: !user && token.trim() ? token.trim() : undefined,
        },
      );

      console.log("🔥 RAW RESPONSE FROM BACKEND:", data);

      const userId = "userId";
      const source = data.source || "mock";

      const queryParams = new URLSearchParams({
        userId,
        questionType,
        numQuestions: numQuestions.toString(),
        profession,
        customInstruction,
        audienceType,
        difficultyLevel,
        source,
      }).toString();

      router.push(`/quiz_display?${queryParams}`);
    } catch (error) {
      console.error(error);
      setErrorMessage("Failed to generate quiz. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-[#f7f8fa] rounded-xl p-10 shadow-lg">
      <form onSubmit={(e) => e.preventDefault()}>
        <QuizGenerationSection
          profession={profession}
          setProfession={setProfession}
          audienceType={audienceType}
          setAudienceType={setAudienceType}
          customInstruction={customInstruction}
          setCustomInstruction={setCustomInstruction}
          numQuestions={numQuestions}
          setNumQuestions={setNumQuestions}
          questionType={questionType}
          setQuestionType={setQuestionType}
          difficultyLevel={difficultyLevel}
          setDifficultyLevel={setDifficultyLevel}
          token={token}
          setToken={setToken}
          previousToken={previousToken}
        />
        {errorMessage && (
          <p className="text-red-500 mb-4 font-medium">{errorMessage}</p>
        )}
        <GenerateButton onClick={handleGenerateQuiz} loading={loading} />
      </form>
    </div>
  );
}
