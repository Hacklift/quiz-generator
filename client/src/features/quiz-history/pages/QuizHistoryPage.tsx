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

interface QuizHistoryQuestion {
  question: string;
  options?: string[];
  answer: string;
}

interface LiveQuizStats {
  invited_participants: number;
  joined_participants: number;
  completed_participants: number;
  average_score?: number | null;
  best_score?: number | null;
  quiz_status: string;
}

interface QuizHistoryItem {
  id?: string;
  _id?: string;
  quiz_id?: string;
  created_at?: string;
  quiz_name?: string;
  question_type: string;
  difficulty_level?: string;
  profession?: string;
  audience_type?: string;
  live_quiz_enabled?: boolean;
  live_quiz_stats?: LiveQuizStats | null;
  invited_participants?: number;
  joined_participants?: number;
  completed_participants?: number;
  average_score?: number | null;
  best_score?: number | null;
  quiz_status?: string;
  questions: QuizHistoryQuestion[];
}

const getQuizHistoryId = (quizItem: Partial<QuizHistoryItem>) =>
  quizItem._id || quizItem.id || "";

const DisplayQuizHistoryPage = ({
  quizHistory,
  onDelete,
}: {
  quizHistory: QuizHistoryItem[];
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
              No quiz history available.
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
                      Generated on:{" "}
                      {quizItem.created_at
                        ? new Date(quizItem.created_at).toLocaleString()
                        : "Unknown date"}
                    </p>
                    <h2 className="text-lg font-semibold text-[#0F2654]">
                      {quizItem.profession ||
                        quizItem.quiz_name ||
                        "Quiz History Item"}
                    </h2>
                    <p className="text-sm text-gray-600">
                      {quizItem.question_type} ·{" "}
                      {quizItem.difficulty_level || "N/A"}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    {quizItem.live_quiz_enabled && quizItem.quiz_id && (
                      <button
                        onClick={() =>
                          router.push(`/my-live-quizzes/${quizItem.quiz_id}`)
                        }
                        className="px-3 py-1 rounded-lg border border-[#0a3264] text-[#0a3264] text-sm hover:bg-blue-50"
                      >
                        Live Dashboard
                      </button>
                    )}
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

                {quizItem.live_quiz_enabled && (
                  <div className="mb-4 grid gap-3 rounded-md border border-blue-100 bg-blue-50 p-3 text-sm text-slate-700 sm:grid-cols-3">
                    <span>
                      Invited:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.invited_participants ??
                          quizItem.invited_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      Joined:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.joined_participants ??
                          quizItem.joined_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      Completed:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.completed_participants ??
                          quizItem.completed_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      Average:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.average_score ??
                          quizItem.average_score ??
                          "-"}
                      </strong>
                    </span>
                    <span>
                      Best:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.best_score ??
                          quizItem.best_score ??
                          "-"}
                      </strong>
                    </span>
                    <span>
                      Status:{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.quiz_status ??
                          quizItem.quiz_status ??
                          "not_live"}
                      </strong>
                    </span>
                  </div>
                )}

                <div className="space-y-4">
                  {quizItem.questions.map((quizQuestion, qIndex) => (
                    <div key={qIndex} className="mb-4">
                      <h3 className="font-semibold text-gray-800 text-base sm:text-lg mb-1">
                        {qIndex + 1}. {quizQuestion.question}
                      </h3>

                      {quizQuestion.options && (
                        <ul className="ml-4 list-disc list-inside text-sm text-gray-700">
                          {quizQuestion.options.map((option, optIdx) => (
                            <li key={optIdx} className="py-0.5">
                              {option}
                            </li>
                          ))}
                        </ul>
                      )}

                      <p className="mt-1 text-sm text-[#0F2654]">
                        <strong>Answer:</strong> {quizQuestion.answer}
                      </p>
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
              Are you sure you want to delete this quiz history item? This
              action cannot be undone.
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
  const [quizHistory, setQuizHistory] = useState<QuizHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchQuizHistory = async () => {
      try {
        const rawHistory: QuizHistoryItem[] =
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
              toast.success("Quiz history item deleted.");
            } catch (error) {
              console.error("Failed to delete quiz history item:", error);
              toast.error("Failed to delete quiz history item.");
            }
          }}
        />
      </Suspense>
    </RequireAuth>
  );
}
