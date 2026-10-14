import { useTranslation } from "react-i18next";
import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import GuestSignupPopup from "@features/live-quiz/components/GuestSignupPopup";
import {
  LiveQuizSessionState,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

interface LiveQuizResultsPageProps {
  sessionId: string;
}

const LiveQuizResultsPage: React.FC<LiveQuizResultsPageProps> = ({
  sessionId,
}) => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const [session, setSession] = useState<LiveQuizSessionState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showSignup, setShowSignup] = useState(false);

  useEffect(() => {
    const loadResult = async () => {
      try {
        setIsLoading(true);
        const data = await liveQuizService.getSession(sessionId);
        setSession(data);
        setShowSignup(
          data.status === "submitted" && router.query.completed === "1",
        );
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Could not load results.");
      } finally {
        setIsLoading(false);
      }
    };
    loadResult();
  }, [router.query.completed, sessionId]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <section className="mx-auto max-w-xl rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-[#0F2654]">
          {uiText("m13aa4cadf07304d9")}
        </h1>
        {session ? (
          <div className="mt-6 divide-y divide-slate-200 rounded-md border border-slate-200">
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">
                {uiText("m554f4235112e7913")}
              </span>
              <span className="text-right text-slate-900">
                {session.participant_name}
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">
                {uiText("m38e5a46cbc5ad328")}
              </span>
              <span className="text-right text-slate-900">
                {session.score}/{session.total_questions}
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">
                {uiText("m379db318f5b44fcd")}
              </span>
              <span className="text-right text-slate-900">
                {session.percentage}%
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">
                {uiText("m920e413c7d411b61")}
              </span>
              <span className="text-right text-slate-900">
                {session.auto_submitted
                  ? uiText("m5c2981214763cb2e")
                  : uiText("m64900440a8c9a5ed")}
              </span>
            </div>
            {session.submitted_at && (
              <div className="flex justify-between gap-4 px-4 py-3 text-sm">
                <span className="font-semibold text-slate-600">
                  {uiText("m2290bea1f250b3fc")}
                </span>
                <span className="text-right text-slate-900">
                  {new Date(session.submitted_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-600">
            {uiText("ma1286c3b41c13c44")}
          </p>
        )}
      </section>
      <GuestSignupPopup
        isOpen={showSignup}
        onClose={() => setShowSignup(false)}
      />
    </main>
  );
};

export const getServerSideProps: GetServerSideProps<
  LiveQuizResultsPageProps
> = async ({ params }) => ({
  props: {
    sessionId: String(params?.sessionId || ""),
  },
});

export default LiveQuizResultsPage;
