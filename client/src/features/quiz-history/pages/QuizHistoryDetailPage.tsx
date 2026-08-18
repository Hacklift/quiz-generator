"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import RequireAuth from "@features/auth/components/RequireAuth";
import { getQuizHistoryItem } from "@features/quiz-history/api/quizHistoryApi";

interface QuizAttemptQuestion {
  question: string;
  user_answer?: string | number | null;
  correct_answer?: string | number | null;
  question_type: string;
  accuracy_percentage?: number | null;
  is_correct: boolean;
  result: string;
}

interface QuizAttemptItem {
  id?: string;
  _id?: string;
  quiz_id: string;
  quiz_title?: string | null;
  score: number;
  percentage: number;
  total_questions: number;
  submitted_at?: string;
  question_results: QuizAttemptQuestion[];
}

export default function QuizHistoryDetailsPage() {
  const router = useRouter();
  const { historyId } = router.query;
  const [item, setItem] = useState<QuizAttemptItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!historyId || Array.isArray(historyId)) return;

    const fetchItem = async () => {
      try {
        const response = await getQuizHistoryItem(historyId);
        setItem(response);
      } catch (error) {
        console.error("Failed to fetch quiz attempt:", error);
        toast.error("Failed to load quiz attempt details.");
      } finally {
        setLoading(false);
      }
    };

    fetchItem();
  }, [historyId]);

  return (
    <RequireAuth
      title="Quiz History Details"
      description="Sign in to view quiz attempt details."
    >
      <div className="flex flex-col min-h-screen bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={() => router.push("/quiz_history")}
              className="mb-4 text-sm text-blue-600 hover:underline"
            >
              ← Back to Quiz History
            </button>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
              </div>
            ) : !item ? (
              <div className="bg-white p-8 rounded-xl shadow-md border border-gray-200 text-center text-gray-600">
                Quiz attempt not found.
              </div>
            ) : (
              <div className="bg-white p-6 rounded-xl shadow-md border border-gray-200">
                <h1 className="text-3xl font-bold text-[#0F2654] mb-2">
                  {item.quiz_title || "Quiz Attempt"}
                </h1>
                <p className="text-sm text-gray-500 mb-1">
                  Submitted on:{" "}
                  {item.submitted_at
                    ? new Date(item.submitted_at).toLocaleString()
                    : "Unknown date"}
                </p>
                <p className="text-sm text-gray-600 mb-1">
                  Score: {item.score}/{item.total_questions}
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  Percentage: {item.percentage.toFixed(0)}%
                </p>

                <div className="mb-6 grid gap-3 rounded-md border border-[#0F2654]/10 bg-[#f8fbff] p-3 text-sm text-slate-700 sm:grid-cols-3">
                  <span>
                    Correct: <strong>{item.score}</strong>
                  </span>
                  <span>
                    Incorrect:{" "}
                    <strong>{item.total_questions - item.score}</strong>
                  </span>
                  <span>
                    Retry set:{" "}
                    <strong>
                      {
                        item.question_results.filter(
                          (question) => !question.is_correct,
                        ).length
                      }
                    </strong>
                  </span>
                </div>

                <div className="space-y-5">
                  {item.question_results.map((question, index) => (
                    <div
                      key={index}
                      className={`rounded-lg border p-4 ${
                        question.is_correct
                          ? "border-emerald-200 bg-emerald-50/60"
                          : "border-amber-200 bg-amber-50/60"
                      }`}
                    >
                      <h2 className="font-semibold text-gray-800 mb-2">
                        {index + 1}. {question.question}
                      </h2>
                      <p className="text-sm text-gray-600 mb-2">
                        {question.question_type} · {question.result}
                      </p>
                      <p className="text-sm text-slate-700">
                        <strong>Your answer:</strong>{" "}
                        {question.user_answer?.toString() || "No answer"}
                      </p>
                      <p className="text-sm text-[#0F2654]">
                        <strong>Correct answer:</strong>{" "}
                        {question.correct_answer?.toString() || "Unavailable"}
                      </p>
                      {typeof question.accuracy_percentage === "number" && (
                        <p className="text-sm text-slate-700 mt-1">
                          <strong>Accuracy:</strong>{" "}
                          {question.accuracy_percentage.toFixed(0)}%
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
