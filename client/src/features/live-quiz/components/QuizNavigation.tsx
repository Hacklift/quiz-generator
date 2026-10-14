import { useTranslation } from "react-i18next";
import React from "react";

interface QuizNavigationProps {
  isFirst: boolean;
  isLast: boolean;
  disabled?: boolean;
  onPrevious?: () => void;
  onNext: () => void;
  onSubmit: () => void;
}

const QuizNavigation: React.FC<QuizNavigationProps> = ({
  isFirst,
  isLast,
  disabled,
  onPrevious,
  onNext,
  onSubmit,
}) => {
  const { t: uiText } = useTranslation("ui");
  return (
    <div className="flex items-center justify-between gap-3">
      {onPrevious ? (
        <button
          type="button"
          onClick={onPrevious}
          disabled={disabled || isFirst}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {uiText("ma57b08a480b822a0")}
        </button>
      ) : (
        <span />
      )}
      <button
        type="button"
        onClick={isLast ? onSubmit : onNext}
        disabled={disabled}
        className="rounded-md bg-[#0a3264] px-5 py-2 text-sm font-semibold text-white transition hover:bg-[#082952] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLast ? uiText("m155f816c0407310c") : uiText("m1ff57a29d7c9d11b")}
      </button>
    </div>
  );
};

export default QuizNavigation;
