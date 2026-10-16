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
                {session.answers_released === false
                  ? "Pending release"
                  : `${session.score ?? "-"}/${session.total_questions}`}
              </span>
            </div>
            <div className="flex justify-between gap-4 px-4 py-3 text-sm">
              <span className="font-semibold text-slate-600">Percentage</span>
              <span className="text-right text-slate-900">
                {session.answers_released === false
                  ? "Pending release"
                  : `${session.percentage ?? "-"}%`}
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

        {session && session.answers_released === false && (
          <div className="mt-6 rounded-md border border-amber-300 bg-amber-50 p-4 text-amber-900">
            <h2 className="font-bold text-amber-950">Answers Withheld Until Deadline</h2>
            <p className="mt-1 text-sm leading-relaxed text-amber-800">
              Your submission has been recorded. Per assignment settings, detailed answers and explanations will be released{" "}
              {session.release_answers_at ? (
                <>after the assignment window closes on <strong>{new Date(session.release_answers_at).toLocaleString()}</strong>.</>
              ) : (
                "when the assignment closes."
              )}
            </p>
          </div>
        )}

        {session && session.answers_released !== false && session.graded_answers && session.graded_answers.length > 0 && (
          <div className="mt-8">
            <h2 className="text-xl font-bold text-[#0F2654]">Question Results & Explanations</h2>
            <div className="mt-4 space-y-4">
              {session.graded_answers.map((answer) => (
                <div
                  key={answer.question_index}
                  className={`rounded-lg border p-4 text-sm transition ${
                    answer.is_correct === true
                      ? "border-emerald-200 bg-emerald-50/50"
                      : answer.is_correct === false
                      ? "border-rose-200 bg-rose-50/50"
                      : "border-slate-200 bg-slate-50/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-slate-900">
                      {answer.question_index + 1}. {answer.question}
                    </h3>
                    {answer.is_correct !== null && answer.is_correct !== undefined && (
                      <span
                        className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${
                          answer.is_correct
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {answer.is_correct ? "✓ Correct" : "✗ Incorrect"}
                      </span>
                    )}
                  </div>

                  <div className="mt-3 space-y-1 text-slate-700">
                    <p>
                      <strong>Your answer:</strong> {answer.selected_answer || "No answer"}
                    </p>
                    {answer.correct_answer && (
                      <p className={answer.is_correct ? "text-emerald-900 font-medium" : "text-[#0F2654] font-medium"}>
                        <strong>Correct answer:</strong> {answer.correct_answer}
                      </p>
                    )}
                  </div>

                  {answer.explanation ? (
                    <div className="mt-3 rounded-md border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-800 shadow-sm">
                      <strong className="block text-slate-900 mb-1">💡 Explanation:</strong>
                      {answer.explanation}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
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
