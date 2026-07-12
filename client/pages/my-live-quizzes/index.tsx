"use client";

import React, { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  LiveQuizSummary,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

const formatDateTime = (isoString: string | null | undefined): string => {
  if (!isoString) return "-";
  try {
    return new Date(isoString).toLocaleString();
  } catch {
    return "-";
  }
};

const tomorrowLocalValue = () => {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
};

const isExpired = (expiresAt: string | null | undefined) =>
  !expiresAt || new Date(expiresAt).getTime() <= Date.now();

const statusLabel: Record<string, string> = {
  active: "Active",
  in_progress: "In Progress",
  completed: "Completed",
  expired: "Expired",
};

const statusClass: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-slate-100 text-slate-700",
  expired: "bg-red-100 text-red-700",
};

const MyLiveQuizzesPage: React.FC = () => {
  const router = useRouter();
  const [quizzes, setQuizzes] = useState<LiveQuizSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [quizToGenerateFor, setQuizToGenerateFor] =
    useState<LiveQuizSummary | null>(null);
  const [duration, setDuration] = useState(20);
  const [expiresAt, setExpiresAt] = useState(tomorrowLocalValue());
  const [isGenerating, setIsGenerating] = useState(false);

  const loadLiveQuizzes = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await liveQuizService.listLiveQuizzes();
      setQuizzes(data);
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not load live quizzes.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLiveQuizzes();
  }, [loadLiveQuizzes]);

  const openGenerationDialog = (quiz: LiveQuizSummary) => {
    setQuizToGenerateFor(quiz);
    setDuration(quiz.time_limit_minutes || 20);
    setExpiresAt(tomorrowLocalValue());
  };

  const generateAccessCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!quizToGenerateFor) return;

    try {
      setIsGenerating(true);
      const response = await liveQuizService.createAccessCode({
        quizId: quizToGenerateFor.quiz_id,
        time_limit_minutes: duration,
        access_code_expires_at: new Date(expiresAt).toISOString(),
        participant_access_mode:
          quizToGenerateFor.participant_access_mode || "public",
        invited_emails: quizToGenerateFor.invited_emails || [],
      });
      setQuizToGenerateFor(null);
      await loadLiveQuizzes();
      toast.success(`Access code ${response.access_code} generated.`);
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not generate access code.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <RequireAuth
      title="Live Quizzes"
      description="Sign in to manage your live quizzes."
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-6xl space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-[#0F2654]">
                  Live Quizzes
                </h1>
                <p className="mt-1 text-sm text-gray-500">
                  Manage access codes and monitor participant activity.
                </p>
              </div>
              <button
                type="button"
                onClick={() => router.push("/generate")}
                className="rounded-md bg-[#0a3264] px-4 py-2 text-sm font-semibold text-white hover:bg-[#082952]"
              >
                Create Quiz
              </button>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-12">
                <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
              </div>
            ) : quizzes.length === 0 ? (
              <div className="rounded-md border border-slate-200 bg-white p-10 text-center text-gray-500 shadow-sm">
                No live quizzes yet.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Quiz
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Access Code
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Status
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Created
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Participants
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Completed
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        Avg Score
                      </th>
                      <th className="px-5 py-3 text-right text-xs font-semibold uppercase text-slate-500">
                        Details
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {quizzes.map((quiz) => (
                      <tr key={quiz.quiz_id} className="hover:bg-slate-50">
                        <td className="px-5 py-4 text-sm font-semibold text-slate-900">
                          {quiz.title}
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">
                          {quiz.access_code ? (
                            <div className="space-y-1">
                              <p className="font-mono tracking-wider text-[#0F2654]">
                                {quiz.access_code}
                              </p>
                              <p className="text-xs text-slate-500">
                                Expires{" "}
                                {formatDateTime(quiz.access_code_expires_at)}
                              </p>
                              {isExpired(quiz.access_code_expires_at) && (
                                <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                                  Expired
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500">No code</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-sm">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              statusClass[quiz.status] ||
                              "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {statusLabel[quiz.status] || quiz.status}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-600">
                          {formatDateTime(quiz.created_at)}
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">
                          {quiz.participant_count}
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">
                          {quiz.completed_count}
                        </td>
                        <td className="px-5 py-4 text-sm text-slate-700">
                          {quiz.average_score ?? "-"}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <div className="flex justify-end gap-2">
                            {(!quiz.access_code ||
                              isExpired(quiz.access_code_expires_at)) && (
                              <button
                                type="button"
                                onClick={() => openGenerationDialog(quiz)}
                                className="rounded-md bg-[#0a3264] px-3 py-1.5 text-sm font-semibold text-white hover:bg-[#082952]"
                              >
                                {quiz.access_code
                                  ? "Generate New Access Code"
                                  : "Generate Access Code"}
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() =>
                                router.push(`/my-live-quizzes/${quiz.quiz_id}`)
                              }
                              className="rounded-md border border-[#0a3264] px-3 py-1.5 text-sm font-semibold text-[#0a3264] hover:bg-blue-50"
                            >
                              View Details
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </main>
        {quizToGenerateFor && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
            <form
              onSubmit={generateAccessCode}
              className="w-full max-w-md rounded-md bg-white p-5 shadow-xl"
            >
              <h2 className="text-lg font-bold text-[#0F2654]">
                {quizToGenerateFor.access_code
                  ? "Generate New Access Code"
                  : "Generate Access Code"}
              </h2>
              <div className="mt-4 space-y-4">
                <label className="block text-sm font-semibold text-slate-700">
                  Duration minutes
                  <input
                    type="number"
                    min={1}
                    max={1440}
                    value={duration}
                    onChange={(event) =>
                      setDuration(Number(event.target.value))
                    }
                    className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
                  />
                </label>
                <label className="block text-sm font-semibold text-slate-700">
                  Access code expires
                  <input
                    type="datetime-local"
                    value={expiresAt}
                    onChange={(event) => setExpiresAt(event.target.value)}
                    className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
                  />
                </label>
              </div>
              <div className="mt-5 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setQuizToGenerateFor(null)}
                  disabled={isGenerating}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="rounded-md bg-[#0a3264] px-3 py-2 text-sm font-semibold text-white hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isGenerating ? "Generating..." : "Generate"}
                </button>
              </div>
            </form>
          </div>
        )}
        <Footer />
      </div>
    </RequireAuth>
  );
};

export default MyLiveQuizzesPage;
