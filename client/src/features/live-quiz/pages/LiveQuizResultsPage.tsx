import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import Link from "next/link";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import GuestSignupPopup from "@features/live-quiz/components/GuestSignupPopup";
import {
  useLivePageLifecycle,
  type LivePageLifecycle,
} from "@features/live-quiz/hooks/useLivePageLifecycle";
import { ROUTES } from "@shared/config/patterns/routes";
import {
  LiveQuizSessionState,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

interface LiveQuizResultsPageProps {
  sessionId: string;
}

function LiveQuizResults({
  sessionId,
  lifecycle,
}: LiveQuizResultsPageProps & { lifecycle: LivePageLifecycle }) {
  const router = useRouter();
  const { capture } = lifecycle;
  const [session, setSession] = useState<LiveQuizSessionState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [signupDismissed, setSignupDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const guard = capture();
    const isCurrent = () => !cancelled && guard();
    const loadResult = async () => {
      try {
        setIsLoading(true);
        const data = await liveQuizService.getSession(sessionId);
        if (!isCurrent()) return;
        setSession(data);
      } catch (error: any) {
        if (isCurrent()) {
          toast.error(error?.response?.data?.detail || "Could not load results.");
        }
      } finally {
        if (isCurrent()) setIsLoading(false);
      }
    };
    loadResult();
    return () => {
      cancelled = true;
    };
  }, [capture, sessionId]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
      </div>
    );
  }

  const privateAssignment = session?.delivery_kind === "quiz";
  const returnHref = lifecycle.isAuthenticated
    ? privateAssignment
      ? ROUTES.MY_ASSIGNMENTS
      : ROUTES.DASHBOARD
    : ROUTES.HOME;
  const returnLabel = lifecycle.isAuthenticated
    ? privateAssignment
      ? "Back to assigned quizzes"
      : "Back to dashboard"
    : "Back to home";

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-10">
      <section className="mx-auto max-w-xl rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-[#0F2654]">Quiz result</h1>
        {session ? (
          <div className="mt-6 divide-y divide-slate-200 rounded-md border border-slate-200">
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">Participant</span>
              <span className="text-right text-slate-900">
                {session.participant_name}
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">Score</span>
              <span className="text-right text-slate-900">
                {session.score}/{session.total_questions}
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">Percentage</span>
              <span className="text-right text-slate-900">
                {session.percentage}%
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">Status</span>
              <span className="text-right text-slate-900">
                {session.auto_submitted ? "Auto Submitted" : "Submitted"}
              </span>
            </div>
            {session.submitted_at && (
              <div className="flex justify-between gap-4 px-4 py-3 text-sm">
                <span className="font-semibold text-slate-600">
                  Submitted At
                </span>
                <span className="text-right text-slate-900">
                  {new Date(session.submitted_at).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-600">Result unavailable.</p>
        )}
        <Link
          className="mt-6 inline-block font-semibold text-[#0F2654] underline"
          href={returnHref}
        >
          {returnLabel}
        </Link>
      </section>
      <GuestSignupPopup
        isOpen={
          !lifecycle.isAuthenticated &&
          !lifecycle.isLeaving &&
          !signupDismissed &&
          session?.status === "submitted" &&
          router.query.completed === "1"
        }
        onClose={() => setSignupDismissed(true)}
      />
    </main>
  );
}

const LiveQuizResultsPage: React.FC<LiveQuizResultsPageProps> = ({
  sessionId,
}) => {
  const lifecycle = useLivePageLifecycle(sessionId);
  return lifecycle.ready ? (
    <LiveQuizResults
      key={lifecycle.pageKey}
      sessionId={sessionId}
      lifecycle={lifecycle}
    />
  ) : (
    <div
      role="status"
      className="flex min-h-screen items-center justify-center"
    >
      Loading results...
    </div>
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
