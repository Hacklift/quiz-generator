import { QuizAnswerFieldProps } from "../../interfaces/props";
import React from "react";

const QuizAnswerField: React.FC<QuizAnswerFieldProps> = ({
  questionType,
  index,
  onAnswerChange,
  options,
}) => {
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
      <div>
        {options?.map((option, optionIndex) => (
          <div key={optionIndex}>
            <input
              type="radio"
              name={`question-${index}`}
              value={option}
              onChange={handleInputChange}
            />
            <label>{option}</label>
          </div>
        ))}
      </div>
    );
  } else if (questionType === "true-false") {
    return (
      <div>
        {["true", "false"].map((option, optionIndex) => (
          <div key={optionIndex}>
            <input
              type="radio"
              name={`question-${index}`}
              value={option}
              onChange={handleInputChange}
            />
            <label>{option}</label>
          </div>
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
