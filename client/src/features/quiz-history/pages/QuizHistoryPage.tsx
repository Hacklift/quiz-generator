"use client";

import React, { Suspense, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import {
  deleteQuizHistoryItem,
  getUserQuizHistory,
} from "@features/quiz-history/api/quizHistoryApi";
import { useAuth } from "@features/auth/context/authContext";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import RequireAuth from "@features/auth/components/RequireAuth";

interface QuizAttemptQuestion {
  question: string;
  user_answer?: string | number | null;
  correct_answer?: string | number | null;
  is_correct: boolean;
  result: string;
  accuracy_percentage?: number | null;
  question_type: string;
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

const getQuizHistoryId = (quizItem: Partial<QuizAttemptItem>) =>
  quizItem._id || quizItem.id || "";

const DisplayQuizHistoryPage = ({
  quizHistory,
  onDelete,
}: {
  quizHistory: QuizAttemptItem[];
  onDelete: (historyId: string) => Promise<void>;
}) => {
  const router = useRouter();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return;

    setDeletingId(confirmDeleteId);
    try {
      await onDelete(confirmDeleteId);
      setConfirmDeleteId(null);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
            Quiz History
          </h1>

          {quizHistory.length === 0 ? (
            <p className="text-center text-gray-600">
              No graded quiz attempts available yet.
            </p>
          ) : (
            quizHistory.map((quizItem, idx) => (
              <div
                key={getQuizHistoryId(quizItem)}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-200"
              >
                {idx > 0 && <hr className="border-gray-300 my-4" />}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-2">
                      Submitted on:{" "}
                      {quizItem.submitted_at
                        ? new Date(quizItem.submitted_at).toLocaleString()
                        : "Unknown date"}
                    </p>
                    <h2 className="text-lg font-semibold text-[#0F2654]">
                      {quizItem.quiz_title || "Quiz Attempt"}
                    </h2>
                    <p className="text-sm text-gray-600">
                      Score: {quizItem.score}/{quizItem.total_questions} ·{" "}
                      {quizItem.percentage.toFixed(0)}%
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() =>
                        router.push(
                          `/quiz_history/${getQuizHistoryId(quizItem)}`,
                        )
                      }
                      className="px-3 py-1 rounded-lg bg-[#0a3264] text-white text-sm hover:bg-[#082952]"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() =>
                        setConfirmDeleteId(getQuizHistoryId(quizItem))
                      }
                      disabled={deletingId === getQuizHistoryId(quizItem)}
                      className="px-3 py-1 rounded-lg border border-red-200 text-red-600 text-sm hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletingId === getQuizHistoryId(quizItem)
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>

                <div className="mb-4 grid gap-3 rounded-md border border-[#0F2654]/10 bg-[#f8fbff] p-3 text-sm text-slate-700 sm:grid-cols-3">
                  <span>
                    Correct: <strong>{quizItem.score}</strong>
                  </span>
                  <span>
                    Incorrect:{" "}
                    <strong>{quizItem.total_questions - quizItem.score}</strong>
                  </span>
                  <span>
                    Suggested retry set:{" "}
                    <strong>
                      {
                        quizItem.question_results.filter(
                          (item) => !item.is_correct,
                        ).length
                      }
                    </strong>
                  </span>
                </div>

                <div className="space-y-4">
                  {quizItem.question_results.map((quizQuestion, qIndex) => (
                    <div
                      key={qIndex}
                      className={`mb-4 rounded-lg border p-4 ${
                        quizQuestion.is_correct
                          ? "border-emerald-200 bg-emerald-50/60"
                          : "border-amber-200 bg-amber-50/60"
                      }`}
                    >
                      <h3 className="font-semibold text-gray-800 text-base sm:text-lg mb-1">
                        {qIndex + 1}. {quizQuestion.question}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {quizQuestion.question_type} · {quizQuestion.result}
                      </p>
                      <p className="mt-2 text-sm text-slate-700">
                        <strong>Your answer:</strong>{" "}
                        {quizQuestion.user_answer?.toString() || "No answer"}
                      </p>
                      <p className="mt-1 text-sm text-[#0F2654]">
                        <strong>Correct answer:</strong>{" "}
                        {quizQuestion.correct_answer?.toString() ||
                          "Unavailable"}
                      </p>
                      {typeof quizQuestion.accuracy_percentage === "number" && (
                        <p className="mt-1 text-sm text-slate-700">
                          <strong>Accuracy:</strong>{" "}
                          {quizQuestion.accuracy_percentage.toFixed(0)}%
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-lg max-w-sm w-full">
            <h2 className="text-lg font-bold mb-3 text-[#0F2654]">
              Confirm Delete
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to delete this quiz attempt? This action
              cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                disabled={deletingId === confirmDeleteId}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deletingId === confirmDeleteId}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deletingId === confirmDeleteId ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
};

export default function DisplayQuizHistory({
  openLoginModal: _openLoginModal,
}: {
  openLoginModal: () => void;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const [quizHistory, setQuizHistory] = useState<QuizAttemptItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchQuizHistory = async () => {
      try {
        const rawHistory: QuizAttemptItem[] =
          (await getUserQuizHistory()) ?? [];
        setQuizHistory(rawHistory);
      } catch (error) {
        console.error("Failed to fetch quiz history:", error);
        setQuizHistory([]);
      } finally {
        setLoading(false);
      }
    };

    fetchQuizHistory();
  }, [isAuthenticated, isLoading]);

  if (isLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
      </div>
    );
  }

  return (
    <RequireAuth
      title="Quiz History"
      description="Sign in to see your quiz history."
    >
      <Suspense
        fallback={
          <div className="p-8 text-center">Loading quiz history...</div>
        }
      >
        <DisplayQuizHistoryPage
          quizHistory={quizHistory}
          onDelete={async (historyId) => {
            try {
              await deleteQuizHistoryItem(historyId);
              setQuizHistory((prev) =>
                prev.filter((item) => getQuizHistoryId(item) !== historyId),
              );
              toast.success("Quiz attempt deleted.");
            } catch (error) {
              console.error("Failed to delete quiz attempt:", error);
              toast.error("Failed to delete quiz attempt.");
            }
          }}
        />
      </Suspense>
    </RequireAuth>
  );
}
