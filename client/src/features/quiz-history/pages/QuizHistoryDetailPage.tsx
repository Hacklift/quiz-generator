"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import RequireAuth from "@features/auth/components/RequireAuth";
import { getQuizHistoryItem } from "@features/quiz-history/api/quizHistoryApi";

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
  custom_instruction?: string;
  live_quiz_enabled?: boolean;
  live_quiz_stats?: LiveQuizStats | null;
  questions: QuizHistoryQuestion[];
}

export default function QuizHistoryDetailsPage() {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { historyId } = router.query;
  const [item, setItem] = useState<QuizHistoryItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!historyId || Array.isArray(historyId)) return;

    const fetchItem = async () => {
      try {
        const response = await getQuizHistoryItem(historyId);
        setItem(response);
      } catch (error) {
        console.error("Failed to fetch quiz history item:", error);
        toast.error(uiText("m4e85a61a3666a2ec"));
      } finally {
        setLoading(false);
      }
    };

    fetchItem();
  }, [historyId]);

  return (
    <RequireAuth
      title={uiText("m0011785533a281e2")}
      description={uiText("m850818ebef8f5af0")}
    >
      <div className="flex flex-col min-h-screen bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={() => router.push("/quiz_history")}
              className="mb-4 text-sm text-blue-600 hover:underline"
            >
              {uiText("m0677e9d39b9b2abd")}
            </button>

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
              </div>
            ) : !item ? (
              <div className="bg-white p-8 rounded-xl shadow-md border border-gray-200 text-center text-gray-600">
                {uiText("m2843c33157f59386")}
              </div>
            ) : (
              <div className="bg-white p-6 rounded-xl shadow-md border border-gray-200">
                <h1 className="text-3xl font-bold text-[#0F2654] mb-2">
                  {item.profession ||
                    item.quiz_name ||
                    uiText("m7f220de11c1f7c38")}
                </h1>
                <p className="text-sm text-gray-500 mb-1">
                  {uiText("m85f153f51e721d34")}{" "}
                  {item.created_at
                    ? new Date(item.created_at).toLocaleString()
                    : uiText("mad224bb89c8a3fb6")}
                </p>
                <p className="text-sm text-gray-600 mb-1">
                  {uiText("m00a459a7be7f506d")}
                  {item.question_type}
                </p>
                <p className="text-sm text-gray-600 mb-1">
                  {uiText("m0554e44e82a9708d")}
                  {item.difficulty_level || "N/A"}
                </p>
                <p className="text-sm text-gray-600 mb-4">
                  {uiText("m08a4cca03a3c53bb")}
                  {item.audience_type || "N/A"}
                </p>
                {item.live_quiz_enabled && item.quiz_id && (
                  <div className="mb-6">
                    {item.live_quiz_stats && (
                      <div className="mb-4 grid gap-3 rounded-md border border-blue-100 bg-blue-50 p-3 text-sm text-slate-700 sm:grid-cols-3">
                        <span>
                          {uiText("m7b05e32e8323fa92")}{" "}
                          <strong>
                            {item.live_quiz_stats.invited_participants}
                          </strong>
                        </span>
                        <span>
                          {uiText("mff2c57cb2ac25428")}{" "}
                          <strong>
                            {item.live_quiz_stats.joined_participants}
                          </strong>
                        </span>
                        <span>
                          {uiText("m7e10a6053e543656")}{" "}
                          <strong>
                            {item.live_quiz_stats.completed_participants}
                          </strong>
                        </span>
                        <span>
                          {uiText("m8525793870dbc270")}{" "}
                          <strong>
                            {item.live_quiz_stats.average_score ?? "-"}
                          </strong>
                        </span>
                        <span>
                          {uiText("m3a97f5e3b4a72eba")}{" "}
                          <strong>
                            {item.live_quiz_stats.best_score ?? "-"}
                          </strong>
                        </span>
                        <span>
                          {uiText("m755c8b2a9fb11446")}{" "}
                          <strong>{item.live_quiz_stats.quiz_status}</strong>
                        </span>
                      </div>
                    )}
                    <button
                      onClick={() =>
                        router.push(`/my-live-quizzes/${item.quiz_id}`)
                      }
                      className="rounded-lg border border-[#0a3264] px-4 py-2 text-sm font-medium text-[#0a3264] hover:bg-blue-50"
                    >
                      {uiText("m6c510a586e2c99ea")}
                    </button>
                  </div>
                )}
                {item.custom_instruction && (
                  <p className="text-sm text-gray-700 mb-6">
                    <strong>{uiText("m2a97ade3b9234be9")}</strong>{" "}
                    {item.custom_instruction}
                  </p>
                )}

                <div className="space-y-5">
                  {item.questions.map((question, index) => (
                    <div
                      key={index}
                      className="rounded-lg border border-gray-200 bg-gray-50 p-4"
                    >
                      <h2 className="font-semibold text-gray-800 mb-2">
                        {index + 1}. {question.question}
                      </h2>
                      {question.options && question.options.length > 0 && (
                        <ul className="list-disc list-inside text-sm text-gray-700 mb-2">
                          {question.options.map((option, optionIndex) => (
                            <li key={optionIndex}>{option}</li>
                          ))}
                        </ul>
                      )}
                      <p className="text-sm text-[#0F2654]">
                        <strong>{uiText("m64f89cf423ee1a16")}</strong>{" "}
                        {question.answer}
                      </p>
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
