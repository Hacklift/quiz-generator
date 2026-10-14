import { useTranslation } from "react-i18next";
import React from "react";

interface QuizCountdownProps {
  remainingSeconds: number;
}

export const formatRemainingTime = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, totalSeconds);
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes.toString().padStart(2, "0")}:${seconds
    .toString()
    .padStart(2, "0")}`;
};

const QuizCountdown: React.FC<QuizCountdownProps> = ({ remainingSeconds }) => {
  const { t: uiText } = useTranslation("ui");

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
      <p className="text-sm font-semibold uppercase text-slate-500">
        {uiText("m9e65f5595e546c47")}
      </p>
      <p className="mt-3 text-5xl font-extrabold text-[#0F2654] md:text-7xl">
        {formatRemainingTime(remainingSeconds)}
      </p>
    </div>
  );
};

export default QuizCountdown;
