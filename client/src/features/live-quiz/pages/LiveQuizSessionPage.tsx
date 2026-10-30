import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import LiveQuizLayout from "@features/live-quiz/components/LiveQuizLayout";
import QuestionCard from "@features/live-quiz/components/QuestionCard";
import QuizNavigation from "@features/live-quiz/components/QuizNavigation";
import { useLiveQuizTimer } from "@features/live-quiz/hooks/useLiveQuizTimer";
import {
  useLivePageLifecycle,
  type LivePageGuard,
  type LivePageLifecycle,
} from "@features/live-quiz/hooks/useLivePageLifecycle";
import {
  LiveQuizSessionState,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

interface LiveQuizPageProps {
  sessionId: string;
}

class StaleLiveOperation extends Error {}

function LiveQuizSession({
  sessionId,
  lifecycle,
}: LiveQuizPageProps & { lifecycle: LivePageLifecycle }) {
  const router = useRouter();
  const { capture, isLeaving } = lifecycle;
  const [session, setSession] = useState<LiveQuizSessionState | null>(null);
  const sessionRef = useRef<LiveQuizSessionState | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState("");
  const selectedAnswerRef = useRef("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const advancingRef = useRef(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasAutoSubmitted, setHasAutoSubmitted] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [isTimerStopped, setIsTimerStopped] = useState(false);
  const autoSubmitStartedRef = useRef(false);
  const isSubmittingRef = useRef(false);
  const submissionOwner = useRef<object | null>(null);
  const finalizingRef = useRef(false);
  const [canRetrySubmission, setCanRetrySubmission] = useState(false);
  const hasSubmittedRef = useRef(false);
  const hasRedirectedRef = useRef(false);
  const saveTail = useRef<Promise<void>>(Promise.resolve());
  const pendingSaves = useRef(0);
  const saveSequence = useRef(0);
  const latestSaveSequence = useRef(new Map<number, number>());

  const redirectToResults = useCallback(
    (isCurrent: LivePageGuard, completed = false) => {
      if (!isCurrent() || hasRedirectedRef.current) return;

      hasRedirectedRef.current = true;
      setIsTimerStopped(true);
      void router
        .replace(
          `/live-quiz/${sessionId}/results${completed ? "?completed=1" : ""}`,
        )
        .catch(() => {
          if (isCurrent()) {
            hasRedirectedRef.current = false;
            setIsTimerStopped(false);
          }
        });
    },
    [router, sessionId],
  );

  useEffect(() => {
    const disconnect = () => {
      if (
        !sessionRef.current ||
        isSubmittingRef.current ||
        hasSubmittedRef.current ||
        sessionRef.current.status === "submitted"
      ) {
        return;
      }
      // Disconnect is best-effort telemetry, not an answer save. A revoked
      // capability must not create an unhandled rejection during navigation.
      void liveQuizService.markDisconnected(sessionId).catch(() => undefined);
    };
    window.addEventListener("beforeunload", disconnect);
    return () => {
      window.removeEventListener("beforeunload", disconnect);
      disconnect();
    };
  }, [sessionId]);

  const loadSession = useCallback(
    async (isCurrent: LivePageGuard) => {
      if (!isCurrent()) return null;

      const data = await liveQuizService.getSession(sessionId);
      if (!isCurrent()) return null;

      sessionRef.current = data;
      setSession(data);
      selectedAnswerRef.current = data.question?.selected_answer || "";
      setSelectedAnswer(selectedAnswerRef.current);
      if (data.status === "submitted") {
        hasSubmittedRef.current = true;
        setHasSubmitted(true);
        redirectToResults(isCurrent);
      }
      return data;
    },
    [redirectToResults, sessionId],
  );

  useEffect(() => {
    let cancelled = false;
    const guard = capture();
    const isCurrent = () => !cancelled && guard();
    void loadSession(isCurrent)
      .catch((error) => {
        if (!isCurrent()) return;
        toast.error(error?.response?.data?.detail || "Could not load session.");
        void router.replace("/quiz-access").catch(() => undefined);
      })
      .finally(() => {
        if (isCurrent()) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [capture, loadSession, router]);

  const enqueueSave = useCallback(
    (
      questionIndex: number,
      answer: string,
      isCurrent: LivePageGuard,
      nextQuestionIndex?: number,
    ) => {
      const scopeCurrent = capture();
      const sequence = ++saveSequence.current;
      latestSaveSequence.current.set(questionIndex, sequence);
      pendingSaves.current += 1;
      if (isCurrent()) setIsSaving(true);

      const work = saveTail.current.then(async () => {
        if (
          !isCurrent() ||
          autoSubmitStartedRef.current ||
          hasSubmittedRef.current
        ) {
          throw new StaleLiveOperation();
        }
        // Let the in-flight write finish, but skip intermediate edits queued
        // behind it. Manual/Next flushes supersede them with the latest value.
        if (latestSaveSequence.current.get(questionIndex) !== sequence) return;

        await liveQuizService.saveAnswer(
          sessionId,
          questionIndex,
          answer,
          nextQuestionIndex,
        );
      });
      // Recover the scheduling tail only; callers still receive and report the
      // rejected work. A failed autosave cannot skip the final manual save.
      saveTail.current = work.then(
        () => undefined,
        () => undefined,
      );
      return work.finally(() => {
        pendingSaves.current -= 1;
        if (scopeCurrent()) setIsSaving(pendingSaves.current > 0);
      });
    },
    [capture, sessionId],
  );

  const submit = useCallback(
    async (autoSubmitted = false) => {
      const scopeCurrent = capture();
      if (!scopeCurrent() || (!autoSubmitted && advancingRef.current)) return;
      if (
        isSubmittingRef.current &&
        (!autoSubmitted || finalizingRef.current)
      ) {
        return;
      }
      if (
        hasSubmittedRef.current ||
        sessionRef.current?.status === "submitted"
      ) {
        redirectToResults(scopeCurrent);
        return;
      }
      if (autoSubmitted && autoSubmitStartedRef.current) return;

      // Expiry can supersede a manual flush stalled on the network. The old
      // operation must neither submit later nor unlock the newer submission.
      const owner = {};
      submissionOwner.current = owner;
      const isCurrent = () => scopeCurrent() && submissionOwner.current === owner;
      isSubmittingRef.current = true;
      setIsSubmitting(true);
      setCanRetrySubmission(false);
      setIsTimerStopped(autoSubmitted);
      if (autoSubmitted) {
        autoSubmitStartedRef.current = true;
        setHasAutoSubmitted(true);
      }

      let finalizationStarted = false;
      try {
        if (!autoSubmitted && sessionRef.current?.question) {
          await enqueueSave(
            sessionRef.current.question.question_index,
            selectedAnswerRef.current,
            isCurrent,
          );
        }
        if (!isCurrent()) return;
        if (autoSubmitted && pendingSaves.current > 0) {
          toast.error(
            "Time expired. Only answers saved before the deadline can be graded.",
          );
        }

        finalizationStarted = true;
        finalizingRef.current = true;
        setIsTimerStopped(true);
        await liveQuizService.submitSession(sessionId, autoSubmitted);
        if (!isCurrent()) return;

        hasSubmittedRef.current = true;
        setHasSubmitted(true);
        redirectToResults(isCurrent, true);
      } catch (error: any) {
        if (!isCurrent()) return;
        if (!finalizationStarted) {
          setIsTimerStopped(false);
          toast.error(
            error?.response?.data?.detail ||
              "Your answer could not be saved. Please retry before submitting.",
          );
          return;
        }
        if (error?.response?.status === 409 || autoSubmitted) {
          try {
            const data = await loadSession(isCurrent);
            if (!isCurrent()) return;
            if (data?.status !== "submitted") {
              if (autoSubmitted) {
                setCanRetrySubmission(true);
              } else {
                setIsTimerStopped(false);
              }
              toast.error(
                error?.response?.data?.detail ||
                  "Submission was not confirmed. Please try again.",
              );
            }
          } catch {
            if (isCurrent()) redirectToResults(isCurrent);
          }
          return;
        }
        setIsTimerStopped(false);
        toast.error(error?.response?.data?.detail || "Could not submit quiz.");
      } finally {
        if (submissionOwner.current === owner) {
          isSubmittingRef.current = false;
          finalizingRef.current = false;
          if (scopeCurrent()) setIsSubmitting(false);
          submissionOwner.current = null;
        }
      }
    },
    [capture, enqueueSave, loadSession, redirectToResults, sessionId],
  );

  const remainingSeconds = useLiveQuizTimer(
    session?.expires_at,
    session?.server_now,
    session?.remaining_seconds || 0,
    () => {
      void submit(true);
    },
    session?.status === "active" &&
      !hasAutoSubmitted &&
      !hasSubmitted &&
      !isTimerStopped &&
      !isLeaving,
  );

  const handleNext = async () => {
    const isCurrent = capture();
    const question = sessionRef.current?.question;
    if (
      !isCurrent() ||
      !question ||
      advancingRef.current ||
      isSubmittingRef.current ||
      hasSubmittedRef.current ||
      remainingSeconds === 0
    ) {
      return;
    }
    advancingRef.current = true;
    setIsAdvancing(true);
    try {
      const next = Math.min(
        question.question_index + 1,
        sessionRef.current!.total_questions - 1,
      );
      await enqueueSave(
        question.question_index,
        selectedAnswerRef.current,
        isCurrent,
        next,
      );
      if (isCurrent() && !isSubmittingRef.current && !hasSubmittedRef.current) {
        await loadSession(isCurrent);
      }
    } catch (error: any) {
      if (isCurrent()) {
        toast.error(error?.response?.data?.detail || "Could not save answer.");
      }
    } finally {
      advancingRef.current = false;
      if (isCurrent()) setIsAdvancing(false);
    }
  };

  const handleSelect = (answer: string) => {
    const isCurrent = capture();
    const question = sessionRef.current?.question;
    if (
      !isCurrent() ||
      !question ||
      advancingRef.current ||
      isSubmittingRef.current ||
      autoSubmitStartedRef.current ||
      hasSubmittedRef.current ||
      remainingSeconds === 0
    ) {
      return;
    }
    selectedAnswerRef.current = answer;
    setSelectedAnswer(answer);
    void enqueueSave(question.question_index, answer, isCurrent).catch(
      (error) => {
        if (isCurrent() && !(error instanceof StaleLiveOperation)) {
          toast.error(
            error?.response?.data?.detail ||
              "Could not autosave answer. Retry before submitting.",
          );
        }
      },
    );
  };

  if (isLoading || !session) return <LiveQuizLoading />;

  return (
    <LiveQuizLayout
      title={session.title}
      participantName={session.participant_name}
      startedAt={session.started_at}
      timeLimitMinutes={session.time_limit_minutes}
      currentQuestion={session.current_question_index + 1}
      totalQuestions={session.total_questions}
      remainingSeconds={remainingSeconds}
    >
      {!session.question ? (
        <section className="rounded-md border border-slate-200 bg-white p-6 text-center shadow-sm">
          <p className="text-slate-700">Loading question...</p>
        </section>
      ) : (
        <div className="space-y-5">
          <QuestionCard
            question={session.question}
            selectedAnswer={selectedAnswer}
            disabled={
              isLeaving ||
              isAdvancing ||
              isSubmitting ||
              hasAutoSubmitted ||
              hasSubmitted ||
              remainingSeconds === 0
            }
            onSelect={handleSelect}
          />
          {isSaving && (
            <p role="status" className="text-sm text-slate-600">
              Saving answer...
            </p>
          )}
          {canRetrySubmission && (
            <div role="alert">
              <p>
                Submission has not been confirmed. Retry to recover the result.
              </p>
              <button
                type="button"
                disabled={isSubmitting || isLeaving}
                className="font-semibold text-[#0F2654] underline"
                onClick={() => {
                  autoSubmitStartedRef.current = false;
                  void submit(true);
                }}
              >
                Retry submission
              </button>
            </div>
          )}
          <QuizNavigation
            isFirst={session.question.question_index === 0}
            isLast={
              session.question.question_index === session.total_questions - 1
            }
            disabled={
              isLeaving ||
              isAdvancing ||
              isSubmitting ||
              hasAutoSubmitted ||
              hasSubmitted ||
              remainingSeconds === 0
            }
            onNext={() => {
              void handleNext();
            }}
            onSubmit={() => {
              void submit(false);
            }}
          />
        </div>
      )}
    </LiveQuizLayout>
  );
}

function LiveQuizLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100">
      <div
        role="status"
        aria-label="Loading session"
        className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]"
      />
    </div>
  );
}

export default function LiveQuizPage({ sessionId }: LiveQuizPageProps) {
  const lifecycle = useLivePageLifecycle(sessionId);
  return lifecycle.ready ? (
    <LiveQuizSession
      key={lifecycle.pageKey}
      sessionId={sessionId}
      lifecycle={lifecycle}
    />
  ) : (
    <LiveQuizLoading />
  );
}

export const getServerSideProps: GetServerSideProps<LiveQuizPageProps> = async ({
  params,
}) => ({
  props: {
    sessionId: String(params?.sessionId || ""),
  },
});
