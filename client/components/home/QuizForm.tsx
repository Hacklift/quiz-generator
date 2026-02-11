"use client";

import { useState } from "react";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import { useRouter } from "next/navigation";
import axios from "axios";

export default function QuizForm() {
  const [profession, setProfession] = useState("");
  const [audienceType, setAudienceType] = useState("");
  const [customInstruction, setCustomInstruction] = useState("");
  const [numQuestions, setNumQuestions] = useState(1);
  const [questionType, setQuestionType] = useState("multichoice");
  const [difficultyLevel, setDifficultyLevel] = useState("easy");
  const [token, setToken] = useState(""); // optional
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleGenerateQuiz = async () => {
    // ✅ Field-specific validation
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
    // ✅ All good — clear previous errors
    setErrorMessage("");
    setLoading(true);

    try {
      const userId = "userId"; // Replace with actual auth value later
      // ✅ Save token only if provided
      if (token.trim()) {
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/user/token`,
          { token },
        );
      }

      const queryParams = new URLSearchParams({
        userId,
        questionType,
        numQuestions: numQuestions.toString(),
        profession,
        customInstruction,
        audienceType,
        difficultyLevel,
        token,
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
        />
        {errorMessage && (
          <p className="text-red-500 mb-4 font-medium">{errorMessage}</p>
        )}
        <GenerateButton onClick={handleGenerateQuiz} loading={loading} />
      </form>
    </div>
  );
}
