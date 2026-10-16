import { useTranslation } from "react-i18next";
import React from "react";
import QuizCountdown from "./QuizCountdown";

interface LiveQuizLayoutProps {
  title: string;
  participantName?: string;
  startedAt?: string;
  timeLimitMinutes?: number;
  currentQuestion: number;
  totalQuestions: number;
  remainingSeconds: number;
  children: React.ReactNode;
}

const LiveQuizLayout: React.FC<LiveQuizLayoutProps> = ({
  title,
  participantName,
  startedAt,
  timeLimitMinutes,
  currentQuestion,
  totalQuestions,
  remainingSeconds,
  children,
}) => {
  const { t: uiText, i18n } = useTranslation("ui");
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <header className="mb-5 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#0F2654]">{title}</h1>
              <p className="mt-2 text-sm text-slate-600">
                {uiText("md2e1ff01ef5ae201", {
                  value0: currentQuestion,
                  value1: totalQuestions,
                })}
              </p>
              {participantName && (
                <p className="mt-1 text-sm text-slate-500">
                  {uiText("m741bdf58a758dc01", { value0: participantName })}
                </p>
              )}
              {startedAt && (
                <p className="mt-1 text-xs text-slate-500">
                  {uiText("ma32cf4f0849fc1f4", {
                    value0: new Date(startedAt).toLocaleTimeString(
                      i18n.language,
                    ),
                  })}
                </p>
              )}
              {timeLimitMinutes && (
                <p className="mt-1 text-xs text-slate-500">
                  {uiText("m64843b676fb4950a", { value0: timeLimitMinutes })}
                </p>
              )}
            </div>
            <QuizCountdown remainingSeconds={remainingSeconds} />
          </div>
        </header>
        {children}
      </div>
    </main>
  );
};

export default LiveQuizLayout;
