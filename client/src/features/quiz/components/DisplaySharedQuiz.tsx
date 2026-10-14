import { useTranslation } from "react-i18next";
import React from "react";
import { DisplayQuizProps } from "@shared/types/props/share-display-props";
import { Question } from "@features/quiz/types";

export default function DisplayQuiz({ quiz }: DisplayQuizProps) {
  const { t: uiText } = useTranslation("ui");

  if (!quiz)
    return <div className="text-center p-4">{uiText("m353b426564197522")}</div>;

  const { title, description, quiz_type, questions } = quiz;

  const renderQuestion = (q: Question, idx: number) => {
    return (
      <div key={idx} className="border p-4 rounded-xl shadow-sm bg-white mb-4">
        <p className="font-medium mb-2">
          {idx + 1}. {q.question}
        </p>

        {quiz_type === "multichoice" && q.options && (
          <ul className="space-y-1">
            {q.options.map((opt, i) => (
              <li
                key={i}
                className="pl-3 py-1 border rounded-md hover:bg-gray-50"
              >
                {opt}
              </li>
            ))}
          </ul>
        )}

        {quiz_type === "true-false" && q.options && (
          <div className="space-x-4">
            {q.options.map((opt, i) => (
              <span
                key={i}
                className="inline-block px-3 py-1 border rounded-md hover:bg-gray-50"
              >
                {opt}
              </span>
            ))}
          </div>
        )}

        {quiz_type === "open-ended" && (
          <input
            type="text"
            placeholder={uiText("md078bf7520a710d0")}
            className="mt-2 w-full border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        )}
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-blue-700 mb-2">{title}</h1>
        <p className="text-gray-600 italic">{description}</p>
      </header>

      <section className="space-y-4">
        {questions.map((q, idx) => renderQuestion(q, idx))}
      </section>
    </div>
  );
}
