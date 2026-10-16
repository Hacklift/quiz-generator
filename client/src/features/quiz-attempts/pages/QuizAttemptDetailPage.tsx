"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/router";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useAuth } from "@features/auth/context/authContext";
import Footer from "@features/quiz/components/Footer";
import NavBar from "@features/quiz/components/NavBar";
import { getQuizAttempt } from "@features/quiz-history/api/quizHistoryApi";

interface QuestionResult {
  question: string;
  explanation?: string | null;
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
  const { t: uiText } = useTranslation("ui");

  const { user } = useAuth();
  const router = useRouter();
  return (
    <RequireAuth
      title={uiText("me4f557f07b37e8ad")}
      description={uiText("mccfc2c48ffa86694")}
    >
      <QuizAttemptDetailContent key={`${user?.id}:${router.query.attemptId}`} />
    </RequireAuth>
  );
}

function QuizAttemptDetailContent() {
  const { t: uiText, i18n } = useTranslation("ui");
  const { t } = useTranslation();

  const router = useRouter();
  const { attemptId } = router.query;
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!attemptId || Array.isArray(attemptId)) return;
    let active = true;
    setLoading(true);
    setLoadError(false);
    const loadAttempt = async () => {
      try {
        const result = await getQuizAttempt(attemptId);
        if (active) setAttempt(result);
      } catch (error) {
        console.error("Failed to fetch quiz attempt:", error);
        if (active) {
          setLoadError(true);
          toast.error(uiText("m54b819a3d732973c"));
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    loadAttempt();
    return () => {
      active = false;
    };
  }, [attemptId, reload]);

  return (
    <div className="flex min-h-screen flex-col bg-gray-100">
      <NavBar />
      <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
        <div className="mx-auto max-w-4xl">
          <button
            type="button"
            onClick={() => router.push("/quiz_attempts")}
            className="mb-4 text-sm text-blue-600 hover:underline"
          >
            {uiText("m2a508169be3fdf31")}
          </button>
          {loading ? (
            <p className="text-center text-gray-600">
              {uiText("m43fa26b3a072f77b")}
            </p>
          ) : loadError ? (
            <div role="alert" className="text-center text-gray-600">
              <p>{uiText("m61586e70e3c174a5")}</p>
              <button
                type="button"
                onClick={() => setReload((value) => value + 1)}
                className="mt-2 text-blue-600 underline"
              >
                {uiText("md8b8392e2c542950")}
              </button>
            </div>
          ) : !attempt ? (
            <p className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-600 shadow-md">
              {uiText("m1533297689ffa9d5")}
            </p>
          ) : (
            <article className="rounded-xl border border-gray-200 bg-white p-6 shadow-md">
              <h1 className="text-3xl font-bold text-[#0F2654]">
                {attempt.quiz_title || uiText("m1ad6a88a3bbe09cf")}
              </h1>
              <p className="mt-2 text-sm text-gray-500">
                {uiText("m201ab1d2d5c1637d")}{" "}
                {attempt.submitted_at
                  ? new Date(attempt.submitted_at).toLocaleString(i18n.language)
                  : uiText("mad224bb89c8a3fb6")}
              </p>
              <p className="mt-1 text-sm text-gray-600">
                {uiText("m9689a814f3584ec9")} {attempt.score}/
                {attempt.total_questions} · {attempt.percentage.toFixed(0)}%
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
                      {t(`values.${question.question_type}`, {
                        defaultValue: question.question_type,
                      })}{" "}
                      ·{" "}
                      {question.result === "Correct"
                        ? uiText("attempts.correct")
                        : question.result === "Incorrect"
                          ? uiText("attempts.incorrect")
                          : question.result}
                    </p>
                    {question.options?.length ? (
                      <ul className="mt-2 list-inside list-disc text-sm text-gray-700">
                        {question.options.map((option) => (
                          <li key={option}>{option}</li>
                        ))}
                      </ul>
                    ) : null}
                    <p className="mt-2 text-sm text-slate-700">
                      <strong>{uiText("madceb15c665f2cad")}</strong>{" "}
                      {question.user_answer?.toString() ||
                        uiText("m7e49c68db30e39dc")}
                    </p>
                    <p className="mt-1 text-sm text-[#0F2654]">
                      <strong>{uiText("m4d659fb1085d715b")}</strong>{" "}
                      {question.correct_answer?.toString() ||
                        uiText("mca184496974204a0")}
                    </p>
                    {typeof question.accuracy_percentage === "number" ? (
                      <p className="mt-1 text-sm text-slate-700">
                        <strong>{uiText("m141c19581b3470d1")}</strong>{" "}
                        {question.accuracy_percentage.toFixed(0)}%
                      </p>
                    ) : null}
                    {question.explanation && (
                      <p className="mt-2 text-sm text-slate-700">
                        {question.explanation}
                      </p>
                    )}
                  </section>
                ))}
              </div>
            </article>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
