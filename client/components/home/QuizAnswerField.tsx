import { QuizAnswerFieldProps } from "../../interfaces/props";
import React from "react";

const QuizAnswerField: React.FC<QuizAnswerFieldProps> = ({
  questionType,
  index,
  onAnswerChange,
  options,
  value,
}) => {
  const stripOptionPrefix = (option: string) =>
    option.replace(/^[A-D][\)\.]\s*/i, "").trim();

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    let answerValue: string | number = e.target.value;

    if (questionType === "true-false") {
      answerValue = answerValue === "true" ? 1 : 0;
    }

    onAnswerChange(index, answerValue);
  };

  if (questionType === "multichoice") {
    return (
      <div className="space-y-3">
        {options?.map((option, optionIndex) => (
          <label
            key={optionIndex}
            htmlFor={`question-${index}-option-${optionIndex}`}
            className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-200 bg-white px-3 py-3 text-sm text-gray-800 transition hover:border-[#0F2654] hover:bg-[#F6F8FC]"
          >
            <input
              id={`question-${index}-option-${optionIndex}`}
              type="radio"
              name={`question-${index}`}
              value={option}
              onChange={handleInputChange}
              checked={value === option}
              className="mt-1 h-4 w-4 shrink-0 accent-[#0F2654]"
            />
            <span className="inline-flex min-w-0 items-start gap-3">
              <span className="font-semibold text-[#0F2654]">
                {String.fromCharCode(65 + optionIndex)}.
              </span>
              <span className="break-words leading-relaxed">
                {stripOptionPrefix(option)}
              </span>
            </span>
          </label>
        ))}
      </div>
    );
  } else if (questionType === "true-false") {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        {["true", "false"].map((option, optionIndex) => (
          <label
            key={optionIndex}
            htmlFor={`question-${index}-boolean-${optionIndex}`}
            className="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-3 text-sm text-gray-800 transition hover:border-[#0F2654] hover:bg-[#F6F8FC]"
          >
            <input
              id={`question-${index}-boolean-${optionIndex}`}
              type="radio"
              name={`question-${index}`}
              value={option}
              onChange={handleInputChange}
              checked={value === (option === "true" ? 1 : 0)}
              className="h-4 w-4 shrink-0 accent-[#0F2654]"
            />
            <span className="font-medium capitalize">{option}</span>
          </label>
        ))}
      </div>
    );
  } else if (questionType === "short-answer") {
    return (
      <input
        type="text"
        onChange={handleInputChange}
        placeholder="Type your short answer here"
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
      />
    );
  } else if (questionType === "open-ended") {
    return (
      <textarea
        rows={4}
        onChange={handleInputChange}
        placeholder="Write your detailed answer here"
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
      />
    );
  }

  return null;
};

export default QuizAnswerField;
