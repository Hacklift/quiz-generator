import { GetServerSideProps } from "next";
import { useRouter } from "next/router";
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import LiveQuizLayout from "@features/live-quiz/components/LiveQuizLayout";
import QuestionCard from "@features/live-quiz/components/QuestionCard";
import QuizNavigation from "@features/live-quiz/components/QuizNavigation";
import { useLiveQuizTimer } from "@features/live-quiz/hooks/useLiveQuizTimer";
import {
  LiveQuizSessionState,
  liveQuizService,
} from "@features/live-quiz/api/liveQuizService";

interface LiveQuizPageProps {
  sessionId: string;
}

const LiveQuizPage: React.FC<LiveQuizPageProps> = ({ sessionId }) => {
  const router = useRouter();
  const [session, setSession] = useState<LiveQuizSessionState | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasAutoSubmitted, setHasAutoSubmitted] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [isTimerStopped, setIsTimerStopped] = useState(false);
  const autoSubmitStartedRef = useRef(false);
  const isSubmittingRef = useRef(false);
  const hasSubmittedRef = useRef(false);
  const hasRedirectedRef = useRef(false);

  const redirectToResults = useCallback(
    (completed = false) => {
      if (hasRedirectedRef.current) return;
      hasRedirectedRef.current = true;
      setIsTimerStopped(true);
      router.replace(
        `/live-quiz/${sessionId}/results${completed ? "?completed=1" : ""}`,
      );
    },
    [router, sessionId],
  );

  useEffect(() => {
    const disconnect = () => {
      if (
        isSubmittingRef.current ||
        hasSubmittedRef.current ||
        session?.status === "submitted"
      ) {
        return;
      }
      void liveQuizService.markDisconnected(sessionId);
    };

    window.addEventListener("beforeunload", disconnect);
    return () => {
      window.removeEventListener("beforeunload", disconnect);
      disconnect();
    };
  }, [session?.status, sessionId]);

  useEffect(() => {
    const stopTimer = () => {
      setIsTimerStopped(true);
    };

    router.events.on("routeChangeStart", stopTimer);
    return () => {
      router.events.off("routeChangeStart", stopTimer);
    };
  }, [router.events]);

  const loadSession = useCallback(async () => {
    const data = await liveQuizService.getSession(sessionId);
    setSession(data);
    setSelectedAnswer(data.question?.selected_answer || "");
    if (data.status === "submitted") {
      hasSubmittedRef.current = true;
      setHasSubmitted(true);
      setIsTimerStopped(true);
      redirectToResults();
    }
    return data;
  }, [redirectToResults, sessionId]);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        await loadSession();
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || "Could not load session.");
        router.replace("/quiz-access");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [loadSession, router]);

  const submit = useCallback(
    async (autoSubmitted = false) => {
      if (
        isSubmittingRef.current ||
        hasSubmittedRef.current ||
        session?.status === "submitted"
      ) {
        redirectToResults();
        return;
      }
      if (autoSubmitted) {
        if (autoSubmitStartedRef.current) return;
        autoSubmitStartedRef.current = true;
        setHasAutoSubmitted(true);
      }
      try {
        setIsTimerStopped(true);
        isSubmittingRef.current = true;
        setIsSubmitting(true);
        await liveQuizService.submitSession(sessionId, autoSubmitted);
        hasSubmittedRef.current = true;
        setHasSubmitted(true);
        redirectToResults(true);
      } catch (error: any) {
        if (error?.response?.status === 409 || autoSubmitted) {
          try {
            const data = await loadSession();
            if (data.status === "submitted") {
              hasSubmittedRef.current = true;
              setHasSubmitted(true);
              redirectToResults();
            }
          } catch {
            redirectToResults();
          }
          return;
        }
        setIsTimerStopped(false);
        toast.error(error?.response?.data?.detail || "Could not submit quiz.");
      } finally {
        isSubmittingRef.current = false;
        setIsSubmitting(false);
      }
    },
    [loadSession, redirectToResults, session?.status, sessionId],
  );

  const isTimerRunning =
    session?.status === "active" &&
    !hasAutoSubmitted &&
    !hasSubmitted &&
    !isSubmitting &&
    !isTimerStopped;

  const remainingSeconds = useLiveQuizTimer(
    session?.expires_at,
    session?.server_now,
    session?.remaining_seconds || 0,
    () => submit(true),
    isTimerRunning,
  );

  const saveCurrentAnswer = async (nextQuestionIndex?: number) => {
    if (
      !session?.question ||
      !selectedAnswer.trim() ||
      hasAutoSubmitted ||
      hasSubmitted ||
      remainingSeconds === 0
    ) {
      return;
    }
    setIsSaving(true);
    try {
      await liveQuizService.saveAnswer(
        sessionId,
        session.question.question_index,
        selectedAnswer,
        nextQuestionIndex,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleNext = async () => {
    try {
      const nextQuestionIndex = session?.question
        ? Math.min(
            session.question.question_index + 1,
            session.total_questions - 1,
          )
        : undefined;
      await saveCurrentAnswer(nextQuestionIndex);
      await loadSession();
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || "Could not save answer.");
    }
  };

  const handleSelect = async (answer: string) => {
    if (hasAutoSubmitted || hasSubmitted || remainingSeconds === 0) return;
    setSelectedAnswer(answer);
    if (!session?.question) return;
    try {
      await liveQuizService.saveAnswer(
        sessionId,
        session.question.question_index,
        answer,
      );
    } catch (error: any) {
      toast.error(
        error?.response?.data?.detail || "Could not autosave answer.",
      );
    }
  };

  if (isLoading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-t-2 border-[#0a3264]" />
      </div>
    );
  }

  if (!session.question) {
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
        <section className="rounded-md border border-slate-200 bg-white p-6 text-center shadow-sm">
          <p className="text-slate-700">Loading question...</p>
        </section>
      </LiveQuizLayout>
    );
  }

  const isLast =
    session.question.question_index === session.total_questions - 1;

  return (
    <LiveQuizLayout
      title={session.title}
      participantName={session.participant_name}
      startedAt={session.started_at}
      timeLimitMinutes={session.time_limit_minutes}
      currentQuestion={session.question.question_index + 1}
      totalQuestions={session.total_questions}
      remainingSeconds={remainingSeconds}
    >
      <div className="space-y-5">
        <QuestionCard
          question={session.question}
          selectedAnswer={selectedAnswer}
          disabled={
            isSubmitting ||
            hasAutoSubmitted ||
            hasSubmitted ||
            remainingSeconds === 0
          }
          onSelect={handleSelect}
        />
        <QuizNavigation
          isFirst={session.question.question_index === 0}
          isLast={isLast}
          disabled={
            isSaving ||
            isSubmitting ||
            hasAutoSubmitted ||
            hasSubmitted ||
            remainingSeconds === 0
          }
          onNext={handleNext}
          onSubmit={() => submit(false)}
        />
      </div>
    </LiveQuizLayout>
  );
};

export const getServerSideProps: GetServerSideProps<
  LiveQuizPageProps
> = async ({ params }) => ({
  props: {
    sessionId: String(params?.sessionId || ""),
  },
});

export default LiveQuizPage;
