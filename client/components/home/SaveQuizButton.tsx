"use client";

import React, { useState } from "react";
import toast from "react-hot-toast";
import { saveQuiz } from "../../lib/functions/savedQuiz";

export default function SaveQuizButton({ quizData }: { quizData: any[] }) {
  const [showInput, setShowInput] = useState(false);
  const [quizTitle, setQuizTitle] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    if (!quizData || quizData.length === 0) {
      toast.error("❌ No questions found to save!");
      return;
    }

    if (!quizTitle.trim()) {
      toast.error("Please enter a quiz title.");
      return;
    }

    const questionType =
      quizData[0]?.question_type || quizData[0]?.type || "unknown-type";

    setLoading(true);

    try {
      const formattedQuestions = quizData.map((q) => ({
        question: q.question,
        options: q.options || null,
        question_type: q.question_type || q.type || questionType,
      }));

      await saveQuiz(quizTitle.trim(), questionType, formattedQuestions);
      toast.success("✅ Quiz saved successfully!");
      setQuizTitle("");
      setShowInput(false);
    } catch (err) {
      console.error("Failed to save quiz:", err);
      toast.error("Failed to save quiz. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {!showInput ? (
        <button
          onClick={() => setShowInput(true)}
          className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm"
        >
          Save Quiz
        </button>
      ) : (
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Enter title"
            value={quizTitle}
            onChange={(e) => setQuizTitle(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm w-36"
          />
          <button
            onClick={handleSave}
            disabled={loading}
            className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-3 py-1.5 rounded-xl shadow-md transition text-sm disabled:bg-gray-400"
          >
            {loading ? "Saving..." : "✓"}
          </button>
          <button
            onClick={() => {
              setShowInput(false);
              setQuizTitle("");
            }}
            className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-semibold px-3 py-1.5 rounded-xl shadow-md transition text-sm"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
