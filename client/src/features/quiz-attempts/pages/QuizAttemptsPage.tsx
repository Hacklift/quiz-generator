"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
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
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  return (
    <RequireAuth
      title={uiText("m90c6cbb0f5551411")}
      description={uiText("m5a083c7801eee49d")}
    >
      <QuizAttemptsContent key={user?.id} />
    </RequireAuth>
  );
}

function QuizAttemptsContent() {
  const { t: uiText, i18n } = useTranslation("ui");

  const router = useRouter();
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    const loadAttempts = async () => {
      try {
        const result = await getUserQuizAttempts();
        if (active) setAttempts(result);
      } catch (error) {
        console.error("Failed to fetch quiz attempts:", error);
        if (active) setLoadError(true);
      } finally {
        if (active) setLoading(false);
      }
    };
    loadAttempts();
    return () => {
      active = false;
    };
  }, [reload]);

  const removeAttempt = async (attemptId: string) => {
    if (!window.confirm(uiText("attempts.confirmDelete"))) {
      return;
    }
    setDeletingId(attemptId);
    try {
      await deleteQuizAttempt(attemptId);
      setAttempts((current) =>
        current.filter((attempt) => getAttemptId(attempt) !== attemptId),
      );
      toast.success(uiText("m47ca7dcab0172ff2"));
    } catch (error) {
      console.error("Failed to delete quiz attempt:", error);
      toast.error(uiText("m39567e1f1a212d37"));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-gray-100">
      <NavBar />
      <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
        <div className="mx-auto max-w-4xl space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-3xl font-bold text-[#0F2654]">
              {uiText("me8a5c4f3bd31cff5")}
            </h1>
            <button
              type="button"
              onClick={() => router.push("/quiz_history")}
              className="rounded-lg border border-[#0a3264] px-4 py-2 text-sm font-medium text-[#0a3264] hover:bg-blue-50"
            >
              {uiText("me3c6ad27a038d956")}
            </button>
          </div>
          {loading ? (
            <p className="text-center text-gray-600">
              {uiText("m5f703d2cbd71b602")}
            </p>
          ) : loadError ? (
            <div role="alert" className="text-center text-gray-600">
              <p>{uiText("m170c0a0c51b8d42c")}</p>
              <button
                type="button"
                onClick={() => setReload((value) => value + 1)}
                className="mt-2 text-blue-600 underline"
              >
                {uiText("md8b8392e2c542950")}
              </button>
            </div>
          ) : attempts.length === 0 ? (
            <p className="text-center text-gray-600">
              {uiText("m2bcbaeee42de5b15")}
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
                    {uiText("m201ab1d2d5c1637d")}{" "}
                    {attempt.submitted_at
                      ? new Date(attempt.submitted_at).toLocaleString(
                          i18n.language,
                        )
                      : uiText("mad224bb89c8a3fb6")}
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-[#0F2654]">
                    {attempt.quiz_title || uiText("m1ad6a88a3bbe09cf")}
                  </h2>
                  <p className="mt-1 text-sm text-gray-600">
                    {uiText("m9689a814f3584ec9")} {attempt.score}/
                    {attempt.total_questions} · {attempt.percentage.toFixed(0)}%
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => router.push(`/quiz_attempts/${attemptId}`)}
                      className="rounded-lg bg-[#0a3264] px-3 py-1 text-sm text-white hover:bg-[#082952]"
                    >
                      {uiText("m90789c12d0731b44")}
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
                      {uiText("m926af581275da75d")}
                    </button>
                    <button
                      type="button"
                      onClick={() => removeAttempt(attemptId)}
                      disabled={deletingId === attemptId}
                      className="rounded-lg border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
                    >
                      {deletingId === attemptId
                        ? uiText("m43b5894c3e4e2b24")
                        : uiText("me2d0a54968ead24e")}
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
  );
}
