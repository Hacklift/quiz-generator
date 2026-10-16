import { useTranslation } from "react-i18next";
import React from "react";
import { LiveQuizQuestion } from "@features/live-quiz/api/liveQuizService";

interface QuestionCardProps {
  question: LiveQuizQuestion;
  selectedAnswer: string;
  disabled?: boolean;
  onSelect: (answer: string) => void;
}

const QuestionCard: React.FC<QuestionCardProps> = ({
  question,
  selectedAnswer,
  disabled,
  onSelect,
}) => {
  const { t: uiText } = useTranslation("ui");

  const options = question.options || [];

  return (
    <section className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">
        {question.question}
      </h2>

      {options.length > 0 ? (
        <div className="mt-5 space-y-3">
          {options.map((option) => (
            <label
              key={option}
              className={`flex cursor-pointer items-center gap-3 rounded-md border px-4 py-3 text-sm transition ${
                selectedAnswer === option
                  ? "border-[#0a3264] bg-blue-50 text-[#0a3264]"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
              } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
            >
              <input
                type="radio"
                name={`question-${question.question_index}`}
                className="h-4 w-4"
                checked={selectedAnswer === option}
                disabled={disabled}
                onChange={() => onSelect(option)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          value={selectedAnswer}
          disabled={disabled}
          onChange={(event) => onSelect(event.target.value)}
          className="mt-5 min-h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-[#0a3264] focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          placeholder={uiText("md078bf7520a710d0")}
        />
      )}
    </section>
  );
};

export default QuestionCard;
