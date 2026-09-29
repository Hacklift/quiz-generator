"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { getQuizAttempt } from "@features/quiz-history/api/quizHistoryApi";

interface QuestionResult {
  question: string;
  user_answer?: string | number | null;
  correct_answer?: string | number | null;
  options?: string[] | null;
  question_type: string;
  accuracy_percentage?: number | null;
  is_correct: boolean;
  result: string;
}

interface QuizAttempt {
  quiz_title?: string | null;
  score: number;
  percentage: number;
  total_questions: number;
  submitted_at?: string;
  question_results: QuestionResult[];
}

export default function QuizAttemptDetailPage() {
  const router = useRouter();
  const { attemptId } = router.query;
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!attemptId || Array.isArray(attemptId)) return;
    const loadAttempt = async () => {
      try {
        setAttempt(await getQuizAttempt(attemptId));
      } catch (error) {
        console.error("Failed to fetch quiz attempt:", error);
        toast.error("Failed to load quiz attempt details.");
      } finally {
        setLoading(false);
      }
    };
    loadAttempt();
  }, [attemptId]);

  return (
    <RequireAuth
      title="Quiz attempt details"
      description="Sign in to view this graded attempt."
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-4xl">
            <button
              type="button"
              onClick={() => router.push("/quiz_attempts")}
              className="mb-4 text-sm text-blue-600 hover:underline"
            >
              ← Back to graded attempts
            </button>
            {loading ? (
              <p className="text-center text-gray-600">Loading attempt…</p>
            ) : !attempt ? (
              <p className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-600 shadow-md">
                Quiz attempt not found.
              </p>
            ) : (
              <article className="rounded-xl border border-gray-200 bg-white p-6 shadow-md">
                <h1 className="text-3xl font-bold text-[#0F2654]">
                  {attempt.quiz_title || "Quiz Attempt"}
                </h1>
                <p className="mt-2 text-sm text-gray-500">
                  Submitted on:{" "}
                  {attempt.submitted_at
                    ? new Date(attempt.submitted_at).toLocaleString()
                    : "Unknown date"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  Score: {attempt.score}/{attempt.total_questions} ·{" "}
                  {attempt.percentage.toFixed(0)}%
                </p>
                <div className="mt-6 space-y-5">
                  {attempt.question_results.map((question, index) => (
                    <section
                      key={`${question.question}-${index}`}
                      className={`rounded-lg border p-4 ${question.is_correct ? "border-emerald-200 bg-emerald-50/60" : "border-amber-200 bg-amber-50/60"}`}
                    >
                      <h2 className="font-semibold text-gray-800">
                        {index + 1}. {question.question}
                      </h2>
                      <p className="mt-1 text-sm text-gray-600">
                        {question.question_type} · {question.result}
                      </p>
                      {question.options?.length ? (
                        <ul className="mt-2 list-inside list-disc text-sm text-gray-700">
                          {question.options.map((option) => (
                            <li key={option}>{option}</li>
                          ))}
                        </ul>
                      ) : null}
                      <p className="mt-2 text-sm text-slate-700">
                        <strong>Your answer:</strong>{" "}
                        {question.user_answer?.toString() || "No answer"}
                      </p>
                      <p className="mt-1 text-sm text-[#0F2654]">
                        <strong>Correct answer:</strong>{" "}
                        {question.correct_answer?.toString() || "Unavailable"}
                      </p>
                      {typeof question.accuracy_percentage === "number" ? (
                        <p className="mt-1 text-sm text-slate-700">
                          <strong>Accuracy:</strong>{" "}
                          {question.accuracy_percentage.toFixed(0)}%
                        </p>
                      ) : null}
                    </section>
                  ))}
                </div>
              </article>
            )}
          </div>
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
