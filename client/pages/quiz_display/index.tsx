"use client";

import React, { useState, useEffect, Suspense } from "react";
import axios from "axios";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import {
  CheckButton,
  NewQuizButton,
  QuizAnswerField,
  DownloadQuizButton,
  NavBar,
  Footer,
  ShareButton,
} from "../../components/home";
import { saveQuizToHistory } from "../../lib/functions/saveQuizToHistory";

const QuizDisplayPage: React.FC = () => {
  const searchParams = useSearchParams();
  const questionType = searchParams.get("questionType") || "multichoice";
  const numQuestions = Number(searchParams.get("numQuestions")) || 1;
  const profession = searchParams.get("profession") || "general knowledge";
  const difficultyLevel = searchParams.get("difficultyLevel") || "easy";
  const audienceType = searchParams.get("audienceType") || "students";
  const customInstruction = searchParams.get("customInstruction") || "";
  const userId = searchParams.get("userId") || "defaultUserId"; // ✅ dummy user until auth works
  const token = searchParams.get("token") || "";

  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [userAnswers, setUserAnswers] = useState<(string | number)[]>([]);
  const [isQuizChecked, setIsQuizChecked] = useState<boolean>(false);
  const [quizReport, setQuizReport] = useState<any[]>([]);
  const [quizId, setQuizId] = useState("");

  useEffect(() => {
    const fetchQuizQuestions = async () => {
      const basePayload = {
        question_type: questionType,
        num_questions: numQuestions,
        profession: profession,
        difficulty_level: difficultyLevel,
        audience_type: audienceType,
        custom_instruction: customInstruction,
        token: token,
      };

      try {
        // 🔹 Try AI source first
        const aiResponse = await axios.post(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/get-questions`,
          basePayload,
        );

        const data = aiResponse.data;

        console.log("🔥 RAW RESPONSE FROM BACKEND:", data);

        // ✅ Notify user if AI is down
        if (data?.ai_down) {
          toast.error(data.notification_message || "AI model unavailable.", {
            duration: 4000,
          });
          setQuizId("");
        }

        const questions = data?.questions || [];
        if (!Array.isArray(questions) || questions.length === 0) {
          throw new Error("No quiz questions returned.");
        }

        setQuizQuestions(questions);
        setUserAnswers(Array(questions.length).fill(""));
        setQuizId(data?.quiz_id);
      } catch (error) {
        console.error("❌ Failed to fetch quiz questions:", error);
        toast.error("Failed to fetch quiz questions. Please try again later.");
      }
    };

    fetchQuizQuestions();
  }, [
    questionType,
    numQuestions,
    profession,
    difficultyLevel,
    audienceType,
    customInstruction,
  ]);

  const handleAnswerChange = (index: number, answer: string | number) => {
    const updated = [...userAnswers];
    updated[index] = answer;
    setUserAnswers(updated);
  };

  const checkAnswers = async () => {
    try {
      const payload = quizQuestions.map((q, i) => {
        const correct = q.answer ?? q.correct_answer;
        if (correct === undefined)
          throw new Error(`No answer for ${q.question}`);

        let userAnswer = userAnswers[i];
        let correctAnswer = correct;

        // ✅ Keep true/false as binary values (1 or 0) for backend
        if (q.question_type === "true-false") {
          if (typeof userAnswer === "string") {
            userAnswer = userAnswer.toLowerCase() === "true" ? 1 : 0;
          }
          if (typeof correctAnswer === "string") {
            correctAnswer = correctAnswer.toLowerCase() === "true" ? 1 : 0;
          }
        }

        return {
          question: q.question,
          user_answer: userAnswer,
          correct_answer: correctAnswer,
          question_type: q.question_type,
          source: q.source || "unknown",
        };
      });

      const { data: report } = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/grade-answers`,
        payload,
      );

      // Convert back to "true"/"false" for display
      const transformed = report.map((r: any) =>
        r.question_type === "true-false"
          ? {
              ...r,
              user_answer: r.user_answer == 1 ? "true" : "false",
              correct_answer: r.correct_answer == 1 ? "true" : "false",
            }
          : r,
      );

      setQuizReport(transformed);
      setIsQuizChecked(true);

      // ✅ Save quiz to history only after grading
      await saveQuizToHistory(userId, questionType, quizQuestions);
    } catch (err) {
      console.error("Error checking answers:", err);
      toast.error("Failed to grade your quiz. Please try again.");
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 flex justify-center px-4 sm:px-6 md:px-8 py-8">
        <div className="w-full max-w-4xl space-y-10">
          {/* Quiz Questions Card */}
          <section className="bg-white shadow rounded-xl px-4 sm:px-6 py-6 sm:py-8 border border-gray-200">
            <h1 className="text-xl sm:text-2xl font-bold text-[#0F2654] mb-6">
              {`${questionType.charAt(0).toUpperCase() + questionType.slice(1)} Quiz`}
            </h1>

            <div className="space-y-6">
              {quizQuestions.map((q, i) => (
                <div
                  key={i}
                  className="bg-gray-50 p-4 rounded-md border border-gray-200"
                >
                  <h3 className="font-medium text-gray-800 mb-2 text-sm sm:text-base">
                    {i + 1}. {q.question}
                  </h3>
                  <QuizAnswerField
                    questionType={q.question_type}
                    index={i}
                    onAnswerChange={handleAnswerChange}
                    options={q.options || []}
                  />
                </div>
              ))}
            </div>

            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-4 sm:space-y-0">
              <CheckButton onClick={checkAnswers} />
              <DownloadQuizButton
                quizId={quizId}
                userId={userId}
                question_type={questionType}
                numQuestion={numQuestions}
              />
              <ShareButton />
              {isQuizChecked && <NewQuizButton />}
            </div>
          </section>

          {isQuizChecked && (
            <section className="bg-white shadow rounded-xl px-4 sm:px-6 py-6 sm:py-8 border border-gray-200">
              <h2 className="text-xl sm:text-2xl font-bold text-[#0F2654] mb-4">
                My Quiz Result
              </h2>

              <div className="space-y-4">
                {quizReport.map((r, i) => (
                  <div
                    key={i}
                    className={`p-4 rounded-md border text-sm ${
                      r.is_correct
                        ? "border-green-200 bg-green-50"
                        : "border-red-200 bg-red-50"
                    }`}
                  >
                    <p>
                      <strong>Question:</strong> {r.question}
                    </p>
                    <p>
                      <strong>Your Answer:</strong> {r.user_answer}
                    </p>
                    <p>
                      <strong>Correct:</strong> {r.correct_answer}
                    </p>
                    {r.accuracy_percentage && (
                      <p>
                        <strong>Accuracy:</strong>{" "}
                        {parseFloat(r.accuracy_percentage).toFixed(2)}%
                      </p>
                    )}
                    <p>
                      <strong>Result:</strong> {r.result}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-4 sm:space-y-0">
                <button className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm">
                  Upgrade Plan to Save your Quiz
                </button>
                <NewQuizButton />
              </div>
            </section>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default function DisplayQuiz() {
  return (
    <Suspense fallback={<div>Loading quiz...</div>}>
      <QuizDisplayPage />
    </Suspense>
  );
}
