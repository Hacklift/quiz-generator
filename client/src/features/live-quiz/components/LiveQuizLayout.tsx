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
  const { t: uiText } = useTranslation("ui");
  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8">
      <div className="mx-auto max-w-3xl">
        <header className="mb-5 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#0F2654]">{title}</h1>
              <p className="mt-2 text-sm text-slate-600">
                {uiText("m289aff12b04274cb")}
                {currentQuestion} {uiText("m28391d3bc64ec15c")}
                {totalQuestions}
              </p>
              {participantName && (
                <p className="mt-1 text-sm text-slate-500">
                  {uiText("m94bb7f748e8e6dc8")}
                  {participantName}
                </p>
              )}
              {startedAt && (
                <p className="mt-1 text-xs text-slate-500">
                  {uiText("mc1c86661d27f92f7")}
                  {new Date(startedAt).toLocaleTimeString()}
                </p>
              )}
              {timeLimitMinutes && (
                <p className="mt-1 text-xs text-slate-500">
                  {uiText("ma0447166be423d1a")}
                  {timeLimitMinutes} {uiText("m90e63d85fa1ab2c8")}
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
