"use client";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import {
  deleteQuizAttempt,
  getUserQuizAttempts,
} from "@features/quiz-history/api/quizHistoryApi";

interface QuizAttempt {
  id?: string;
  _id?: string;
  quiz_id: string;
  quiz_title?: string | null;
  score: number;
  percentage: number;
  total_questions: number;
  submitted_at?: string;
}

const getAttemptId = (attempt: QuizAttempt) => attempt._id || attempt.id || "";

export default function QuizAttemptsPage() {
  const router = useRouter();
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const loadAttempts = async () => {
      const result = await getUserQuizAttempts();
      setAttempts(result ?? []);
      setLoading(false);
    };
    loadAttempts();
  }, []);

  const removeAttempt = async (attemptId: string) => {
    if (
      !window.confirm("Delete this quiz attempt? This action cannot be undone.")
    ) {
      return;
    }
    setDeletingId(attemptId);
    try {
      await deleteQuizAttempt(attemptId);
      setAttempts((current) =>
        current.filter((attempt) => getAttemptId(attempt) !== attemptId),
      );
      toast.success("Quiz attempt deleted.");
    } catch (error) {
      console.error("Failed to delete quiz attempt:", error);
      toast.error("Failed to delete quiz attempt.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <RequireAuth
      title="Quiz attempts"
      description="Sign in to view your graded quiz attempts."
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-4xl space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h1 className="text-3xl font-bold text-[#0F2654]">
                Graded Quiz Attempts
              </h1>
              <button
                type="button"
                onClick={() => router.push("/quiz_history")}
                className="rounded-lg border border-[#0a3264] px-4 py-2 text-sm font-medium text-[#0a3264] hover:bg-blue-50"
              >
                Generated quiz history
              </button>
            </div>
            {loading ? (
              <p className="text-center text-gray-600">Loading attempts…</p>
            ) : attempts.length === 0 ? (
              <p className="text-center text-gray-600">
                No graded quiz attempts available yet.
              </p>
            ) : (
              attempts.map((attempt) => {
                const attemptId = getAttemptId(attempt);
                return (
                  <article
                    key={attemptId}
                    className="rounded-xl border border-gray-200 bg-white p-6 shadow-md"
                  >
                    <p className="text-sm text-gray-500">
                      Submitted on:{" "}
                      {attempt.submitted_at
                        ? new Date(attempt.submitted_at).toLocaleString()
                        : "Unknown date"}
                    </p>
                    <h2 className="mt-2 text-lg font-semibold text-[#0F2654]">
                      {attempt.quiz_title || "Quiz Attempt"}
                    </h2>
                    <p className="mt-1 text-sm text-gray-600">
                      Score: {attempt.score}/{attempt.total_questions} ·{" "}
                      {attempt.percentage.toFixed(0)}%
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          router.push(`/quiz_attempts/${attemptId}`)
                        }
                        className="rounded-lg bg-[#0a3264] px-3 py-1 text-sm text-white hover:bg-[#082952]"
                      >
                        View Details
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          router.push(
                            `/quiz_display?quizId=${encodeURIComponent(attempt.quiz_id)}`,
                          )
                        }
                        className="rounded-lg bg-emerald-700 px-3 py-1 text-sm text-white hover:bg-emerald-800"
                      >
                        Retake Quiz
                      </button>
                      <button
                        type="button"
                        onClick={() => removeAttempt(attemptId)}
                        disabled={deletingId === attemptId}
                        className="rounded-lg border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {deletingId === attemptId ? "Deleting…" : "Delete"}
                      </button>
                    </div>
                  </article>
                );
              })
            )}
          </div>
        </main>
        <Footer />
      </div>
    </RequireAuth>
  );
}
