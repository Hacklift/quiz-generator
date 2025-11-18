"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
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
  SaveQuizButton,
} from "../../components/home";
import { saveQuizToHistory } from "../../lib/functions/saveQuizToHistory";
import { useAuth } from "../../contexts/authContext";

const QuizDisplayPage: React.FC = () => {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const savedQuizId = searchParams.get("id");
  const questionType = searchParams.get("questionType") || "multichoice";
  const numQuestions = Number(searchParams.get("numQuestions")) || 1;
  const profession = searchParams.get("profession") || "general knowledge";
  const difficultyLevel = searchParams.get("difficultyLevel") || "easy";
  const audienceType = searchParams.get("audienceType") || "students";
  const customInstruction = searchParams.get("customInstruction") || "";
  const userId = user?.id || "defaultUserId";

  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [userAnswers, setUserAnswers] = useState<(string | number)[]>([]);
  const [isQuizChecked, setIsQuizChecked] = useState(false);
  const [quizReport, setQuizReport] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const fetchQuizQuestions = async () => {
      try {
        setIsLoading(true);
        let questions: any[] = [];

        const storedQuiz = localStorage.getItem("saved_quiz_view");
        if (storedQuiz) {
          const parsedQuiz = JSON.parse(storedQuiz);
          if (parsedQuiz?.questions?.length > 0) {
            setQuizQuestions(parsedQuiz.questions);
            setUserAnswers(Array(parsedQuiz.questions.length).fill(""));
            toast.success(`Loaded saved quiz: ${parsedQuiz.title}`);
            localStorage.removeItem("saved_quiz_view");
            setIsLoading(false);
            return;
          }
        }

        if (savedQuizId) {
          const { data } = await axios.get(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/saved-quizzes/${savedQuizId}`,
          );
          if (!data?.questions?.length)
            throw new Error("No questions found for this saved quiz.");

          questions = data.questions.map((q: any) => ({
            ...q,
            answer: q.answer || q.correct_answer,
          }));

          toast.success("Loaded saved quiz successfully!");
        } else {
          const payload = {
            question_type: questionType,
            num_questions: numQuestions,
            profession,
            difficulty_level: difficultyLevel,
            audience_type: audienceType,
            custom_instruction: customInstruction,
          };

          const { data } = await axios.post(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/get-questions`,
            payload,
          );

          if (data?.ai_down)
            toast.error(data.notification_message || "AI model unavailable.", {
              duration: 4000,
            });
          questions = data?.questions || [];
          if (!Array.isArray(questions) || !questions.length)
            throw new Error("No quiz questions returned.");
          toast.success("Generated new quiz successfully!");
        }

        setQuizQuestions(questions);
        setUserAnswers(Array(questions.length).fill(""));
      } catch (err: any) {
        console.error("❌ Failed to fetch quiz questions:", err);
        toast.error(err.message || "Failed to fetch quiz questions.");
        setQuizQuestions([]);
        setUserAnswers([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuizQuestions();
  }, [
    savedQuizId,
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

        if (q.question_type === "true-false") {
          if (typeof userAnswer === "string")
            userAnswer = userAnswer.toLowerCase() === "true" ? 1 : 0;
          if (typeof correctAnswer === "string")
            correctAnswer = correctAnswer.toLowerCase() === "true" ? 1 : 0;
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

      if (user && !savedQuizId) {
        const meta = {
          question_type: questionType,
          num_questions: numQuestions,
          difficulty_level: difficultyLevel,
          profession,
          audience_type: audienceType,
          custom_instruction: customInstruction,
        };

        await saveQuizToHistory(userId, meta, quizQuestions);
      }
    } catch (err) {
      console.error("Error checking answers:", err);
      toast.error("Failed to grade your quiz. Please try again.");
    }
  };

  if (isLoading)
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0a3264]"></div>
      </div>
    );
  if (!quizQuestions.length)
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p className="text-gray-600 text-center text-lg">
          No quiz questions found.
        </p>
      </div>
    );

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />
      <main className="flex-1 flex justify-center px-4 sm:px-6 md:px-8 py-8">
        <div className="w-full max-w-4xl space-y-10">
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
              <SaveQuizButton quizData={quizQuestions} />
              <DownloadQuizButton
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
                    className={`p-4 rounded-md border text-sm ${r.is_correct ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}
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
                {!user && (
                  <button className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md text-sm">
                    Upgrade Plan to Save your Quiz
                  </button>
                )}
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
