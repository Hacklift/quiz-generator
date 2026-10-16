"use client";
import { useTranslation } from "react-i18next";

import React, { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import RequireAuth from "@features/auth/components/RequireAuth";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import {
  LiveQuizSummary,
  liveQuizService,
  type LiveResultsExportFormat,
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

export const MyLiveQuizzesPage: React.FC = () => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [quizzes, setQuizzes] = useState<LiveQuizSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [quizToGenerateFor, setQuizToGenerateFor] =
    useState<LiveQuizSummary | null>(null);
  const [duration, setDuration] = useState(20);
  const [expiresAt, setExpiresAt] = useState(tomorrowLocalValue());
  const [isGenerating, setIsGenerating] = useState(false);
  const [exportingQuizId, setExportingQuizId] = useState<string | null>(null);
  const [openActionsQuizId, setOpenActionsQuizId] = useState<string | null>(
    null,
  );

  const loadLiveQuizzes = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await liveQuizService.listLiveQuizzes();
      setQuizzes(data);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || uiText("mde02d96b3b3b172b"));
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
      toast.success(
        uiText("me69e4744cb001c89", { value0: response.access_code }),
      );
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || uiText("m1a351ea3a241cfd5"));
    } finally {
      setIsGenerating(false);
    }
  };

  const exportResults = async (
    quiz: LiveQuizSummary,
    format: LiveResultsExportFormat,
  ) => {
    setOpenActionsQuizId(null);
    setExportingQuizId(quiz.quiz_id);
    try {
      const { blob, contentDisposition } =
        await liveQuizService.downloadResults(quiz.quiz_id, format);
      const filename =
        contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1] ||
        `${quiz.title || "live-quiz"}-results.${format}`;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(uiText("m3715d1e17072082a"));
    } catch {
      toast.error(uiText("mebdce5656ec7dbf5"));
    } finally {
      setExportingQuizId(null);
    }
  };

  return (
    <RequireAuth
      title={uiText("mc0706a5f11ed61e6")}
      description={uiText("me952ed1ab232537c")}
    >
      <div className="flex min-h-screen flex-col bg-gray-100">
        <NavBar />
        <main className="flex-1 px-4 py-8 sm:px-6 md:px-8">
          <div className="mx-auto max-w-6xl space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-[#0F2654]">
                  {uiText("mc0706a5f11ed61e6")}
                </h1>
                <p className="mt-1 text-sm text-gray-500">
                  {uiText("m507c8fcf08050b19")}
                </p>
              </div>
              <button
                type="button"
                onClick={() => router.push("/generate")}
                className="rounded-md bg-[#0a3264] px-4 py-2 text-sm font-semibold text-white hover:bg-[#082952]"
              >
                {uiText("mf91277bd9ede04d8")}
              </button>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-12">
                <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
              </div>
            ) : quizzes.length === 0 ? (
              <div className="rounded-md border border-slate-200 bg-white p-10 text-center text-gray-500 shadow-sm">
                {uiText("mc65bedf08fd683b1")}
              </div>
            ) : (
              <div className="overflow-x-auto rounded-md border border-slate-200 bg-white shadow-sm">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("m03aa7dc16797a82b")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("m09916abb4d2c0145")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("m920e413c7d411b61")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("md70b9e24bca26b40")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("m0e27279b3302db04")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("m22a970d2e5b1cc23")}
                      </th>
                      <th className="px-5 py-3 text-left text-xs font-semibold uppercase text-slate-500">
                        {uiText("mb24bd71ded2c3fd6")}
                      </th>
                      <th className="px-5 py-3 text-right text-xs font-semibold uppercase text-slate-500">
                        {uiText("mff8059dc6752afdd")}
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
                                {uiText("m8d16138f121d6ee8", {
                                  value0: formatDateTime(
                                    quiz.access_code_expires_at,
                                  ),
                                })}
                              </p>
                              {isExpired(quiz.access_code_expires_at) && (
                                <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                                  {uiText("m424a2551d356754c")}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500">
                              {uiText("m18756e1616d68789")}
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-sm">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              statusClass[quiz.status] ||
                              "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {uiText("values." + quiz.status, {
                              ns: "translation",
                              defaultValue:
                                statusLabel[quiz.status] || quiz.status,
                            })}
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
                                  ? uiText("m9488f37cfeb2192a")
                                  : uiText("md1bf07cff62cf317")}
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() =>
                                router.push(`/my-live-quizzes/${quiz.quiz_id}`)
                              }
                              className="rounded-md border border-[#0a3264] px-3 py-1.5 text-sm font-semibold text-[#0a3264] hover:bg-blue-50"
                            >
                              {uiText("m90789c12d0731b44")}
                            </button>
                            <div className="relative">
                              <button
                                type="button"
                                aria-label={uiText("m7025f2de2cf460e7", {
                                  value0: quiz.title,
                                })}
                                aria-expanded={
                                  openActionsQuizId === quiz.quiz_id
                                }
                                onClick={() =>
                                  setOpenActionsQuizId((current) =>
                                    current === quiz.quiz_id
                                      ? null
                                      : quiz.quiz_id,
                                  )
                                }
                                disabled={exportingQuizId === quiz.quiz_id}
                                className="rounded-md border border-slate-300 px-3 py-1.5 text-lg font-bold leading-none text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                              >
                                &#8942;
                              </button>
                              {openActionsQuizId === quiz.quiz_id && (
                                <div className="absolute right-0 z-20 mt-2 w-44 rounded-md border border-slate-200 bg-white py-1 text-left shadow-lg">
                                  <p className="px-3 py-1.5 text-xs font-semibold uppercase text-slate-500">
                                    {uiText("m97df6c79050ddf07")}
                                  </p>
                                  {(["csv", "pdf", "txt"] as const).map(
                                    (format) => (
                                      <button
                                        key={format}
                                        type="button"
                                        onClick={() =>
                                          exportResults(quiz, format)
                                        }
                                        className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                                      >
                                        {format === "txt"
                                          ? uiText("m71988c4d8e0803ba")
                                          : format.toUpperCase()}
                                      </button>
                                    ),
                                  )}
                                </div>
                              )}
                            </div>
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
                  ? uiText("m9488f37cfeb2192a")
                  : uiText("md1bf07cff62cf317")}
              </h2>
              <div className="mt-4 space-y-4">
                <label className="block text-sm font-semibold text-slate-700">
                  {uiText("m471195f5d126bfed")}
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
                  {uiText("m6e5ab5d97b456f1c")}
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
                  {uiText("m19766ed6ccb2f4a3")}
                </button>
                <button
                  type="submit"
                  disabled={isGenerating}
                  className="rounded-md bg-[#0a3264] px-3 py-2 text-sm font-semibold text-white hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isGenerating
                    ? uiText("m49286f33b674a0a6")
                    : uiText("m49e49bb4401e67bd")}
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
