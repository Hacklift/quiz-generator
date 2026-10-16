"use client";
import { useTranslation } from "react-i18next";

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
import { useTerms } from "@features/persona/hooks/useTerms";

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
  const { t: uiText, i18n } = useTranslation("ui");

  const router = useRouter();
  const t = useTerms();
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
            {uiText("m0d6eb040a81b42bb", {
              value0: t("quiz").charAt(0).toUpperCase() + t("quiz").slice(1),
            })}
          </h1>

          {quizHistory.length === 0 ? (
            <p className="text-center text-gray-600">
              {uiText("m2f0921cb1113e80c", { value0: t("quiz") })}
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
                      {uiText("m9c6202d152243a60", {
                        value0: quizItem.created_at
                          ? new Date(quizItem.created_at).toLocaleString(
                              i18n.language,
                            )
                          : uiText("mad224bb89c8a3fb6"),
                      })}
                    </p>
                    <h2 className="text-lg font-semibold text-[#0F2654]">
                      {quizItem.profession ||
                        quizItem.quiz_name ||
                        uiText("m7f220de11c1f7c38")}
                    </h2>
                    <p className="text-sm text-gray-600">
                      {uiText("values." + quizItem.question_type, {
                        ns: "translation",
                        defaultValue: quizItem.question_type,
                      })}{" "}
                      · {quizItem.difficulty_level || "N/A"}
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
                        {uiText("m24907a79b7cb41b6")}
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
                      {uiText("m90789c12d0731b44")}
                    </button>
                    <button
                      onClick={() =>
                        setConfirmDeleteId(getQuizHistoryId(quizItem))
                      }
                      disabled={deletingId === getQuizHistoryId(quizItem)}
                      className="px-3 py-1 rounded-lg border border-red-200 text-red-600 text-sm hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletingId === getQuizHistoryId(quizItem)
                        ? uiText("m685ecb984ac29ce8")
                        : uiText("me2d0a54968ead24e")}
                    </button>
                  </div>
                </div>

                {quizItem.live_quiz_enabled && (
                  <div className="mb-4 grid gap-3 rounded-md border border-blue-100 bg-blue-50 p-3 text-sm text-slate-700 sm:grid-cols-3">
                    <span>
                      {uiText("m7b05e32e8323fa92")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.invited_participants ??
                          quizItem.invited_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      {uiText("mff2c57cb2ac25428")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.joined_participants ??
                          quizItem.joined_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      {uiText("m7e10a6053e543656")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.completed_participants ??
                          quizItem.completed_participants ??
                          0}
                      </strong>
                    </span>
                    <span>
                      {uiText("m8525793870dbc270")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.average_score ??
                          quizItem.average_score ??
                          "-"}
                      </strong>
                    </span>
                    <span>
                      {uiText("m3a97f5e3b4a72eba")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.best_score ??
                          quizItem.best_score ??
                          "-"}
                      </strong>
                    </span>
                    <span>
                      {uiText("m755c8b2a9fb11446")}{" "}
                      <strong>
                        {quizItem.live_quiz_stats?.quiz_status ??
                          quizItem.quiz_status ??
                          uiText("m9d598963adc611c1")}
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
                        <strong>{uiText("m64f89cf423ee1a16")}</strong>{" "}
                        {quizQuestion.answer}
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
              {uiText("ma7f54311a3e625f5")}
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              {uiText("m6fe0f689f0a6bf9e")}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                disabled={deletingId === confirmDeleteId}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100 disabled:opacity-50"
              >
                {uiText("m19766ed6ccb2f4a3")}
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={deletingId === confirmDeleteId}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deletingId === confirmDeleteId
                  ? uiText("m685ecb984ac29ce8")
                  : uiText("me2d0a54968ead24e")}
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
  const { t: uiText, i18n } = useTranslation("ui");

  const { isAuthenticated, isLoading } = useAuth();
  const t = useTerms();
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
      title={uiText("m0d6eb040a81b42bb", {
        value0: t("quiz").charAt(0).toUpperCase() + t("quiz").slice(1),
      })}
      description={uiText("m9c17d0cd6388ff9f", { value0: t("quiz") })}
    >
      <Suspense
        fallback={
          <div className="p-8 text-center">
            {uiText("m69df56807e7a5fdc", { value0: t("quiz") })}
          </div>
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
              toast.success(uiText("mb4c897b3cb3e6a84"));
            } catch (error) {
              console.error("Failed to delete quiz history item:", error);
              toast.error(uiText("m8ae0049ae086c914"));
            }
          }}
        />
      </Suspense>
    </RequireAuth>
  );
}
