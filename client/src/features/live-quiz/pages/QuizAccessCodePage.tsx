import { useTranslation } from "react-i18next";
import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { FormEvent, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { NavBar, Footer } from "@features/quiz/components";
import {
  LiveQuizPreview,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

interface QuizAccessPreviewPageProps {
  code: string;
}

const QuizAccessPreviewPage: React.FC<QuizAccessPreviewPageProps> = ({
  code,
}) => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [preview, setPreview] = useState<LiveQuizPreview | null>(null);
  const [participantName, setParticipantName] = useState("");
  const [participantEmail, setParticipantEmail] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    const loadPreview = async () => {
      try {
        setIsLoading(true);
        setPreview(await liveQuizService.validateAccessCode(code));
      } catch (error: any) {
        toast.error(
          error?.response?.data?.detail || "Access code unavailable.",
        );
        router.replace("/quiz-access");
      } finally {
        setIsLoading(false);
      }
    };
    loadPreview();
  }, [code, router]);

  const handleStart = async (event: FormEvent) => {
    event.preventDefault();
    if (!participantName.trim()) {
      toast.error(uiText("mb5cd3b070f53c235"));
      return;
    }

    try {
      setIsStarting(true);
      const session = await liveQuizService.startSession({
        code,
        participant_name: participantName.trim(),
        participant_email: participantEmail.trim() || undefined,
      });
      router.push(session.redirect_url);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not start quiz.");
    } finally {
      setIsStarting(false);
    }
  };

  if (isLoading || !preview) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <NavBar />
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <form
          onSubmit={handleStart}
          className="w-full max-w-xl rounded-md border border-slate-200 bg-white p-6 shadow-sm"
        >
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            {uiText("mfef250162a1277bb")}
          </p>
          <h1 className="mt-2 text-2xl font-bold text-[#0F2654]">
            {preview.title}
          </h1>
          <div className="mt-5 grid gap-3 text-sm text-slate-700 sm:grid-cols-3">
            <div className="rounded-md bg-slate-50 p-3">
              <span className="block font-semibold">
                {uiText("m9a72221a27476f3e")}
              </span>
              {preview.total_questions}
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <span className="block font-semibold">
                {uiText("m4fc52a3c4c558b51")}
              </span>
              {preview.time_limit_minutes} {uiText("m90e63d85fa1ab2c8")}
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <span className="block font-semibold">
                {uiText("m40a35cf6c6bf5fdc")}
              </span>
              {new Date(preview.access_code_expires_at).toLocaleDateString()}
            </div>
          </div>

          <label className="mt-6 block text-sm font-semibold text-slate-700">
            {uiText("mf13a64ba2fea87ef")}
          </label>
          <input
            value={participantName}
            onChange={(event) => setParticipantName(event.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          />

          <label className="mt-4 block text-sm font-semibold text-slate-700">
            {uiText("m969ccbd3cf6300ec")}
          </label>
          <input
            type="email"
            value={participantEmail}
            onChange={(event) => setParticipantEmail(event.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100"
          />

          <button
            type="submit"
            disabled={isStarting}
            className="mt-6 w-full rounded-md bg-[#0a3264] px-4 py-2 text-sm font-semibold text-white hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isStarting
              ? uiText("m82b93630a921dddf")
              : uiText("m56628cf845696718")}
          </button>
        </form>
      </main>
      <Footer />
    </div>
  );
};

export const getServerSideProps: GetServerSideProps<
  QuizAccessPreviewPageProps
> = async ({ params }) => ({
  props: {
    code: String(params?.code || ""),
  },
});

export default QuizAccessPreviewPage;
