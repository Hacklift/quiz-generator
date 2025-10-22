"use client";

import React, { useEffect, useState, Suspense } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import {
  getSavedQuizzes,
  deleteSavedQuiz,
} from "../../lib/functions/savedQuiz";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";

interface QuizQuestion {
  question: string;
  options?: string[];
  correct_answer?: string;
}

interface SavedQuiz {
  _id: string;
  title: string;
  created_at: string;
  questions?: QuizQuestion[];
  question_type?: string;
}

const DisplaySavedQuizzesPage: React.FC<{
  savedQuizzes: SavedQuiz[];
  onDeleteClick: (quizId: string) => void;
}> = ({ savedQuizzes, onDeleteClick }) => {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const router = useRouter();

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return;
    try {
      await deleteSavedQuiz(confirmDeleteId);
      toast.success("Quiz deleted successfully!");
      onDeleteClick(confirmDeleteId);
      setConfirmDeleteId(null);
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete quiz");
    }
  };

  const handleViewQuiz = (quiz: SavedQuiz) => {
    // ✅ Pass quiz data as router state instead of URL reload
    router.push(`/quiz_display?id=${quiz._id}`, {
      scroll: true,
    });

    // Optionally, save quiz data temporarily in localStorage
    // for retrieval in quiz_display page
    localStorage.setItem("saved_quiz_view", JSON.stringify(quiz));
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
            Saved Quizzes
          </h1>

          {savedQuizzes.length === 0 ? (
            <p className="text-center text-gray-600">
              You haven’t saved any quizzes yet.
            </p>
          ) : (
            savedQuizzes.map((quiz) => (
              <div
                key={quiz._id}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-200"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-2">
                      Saved on:{" "}
                      {quiz.created_at
                        ? new Date(quiz.created_at).toLocaleString()
                        : "Unknown date"}
                    </p>
                    <h2 className="text-xl font-bold text-[#0F2654]">
                      {quiz.title}
                    </h2>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setConfirmDeleteId(quiz._id)}
                      className="text-sm text-red-600 hover:text-red-800 font-semibold"
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => handleViewQuiz(quiz)}
                      className="text-sm bg-[#0a3264] hover:bg-[#082952] text-white px-3 py-1 rounded-lg font-semibold"
                    >
                      View Quiz
                    </button>
                  </div>
                </div>

                {quiz.questions && quiz.questions.length > 0 ? (
                  quiz.questions.map((q, idx) => (
                    <div key={idx} className="mb-4">
                      <h3 className="font-semibold text-gray-800 text-base sm:text-lg mb-1">
                        {idx + 1}. {q.question}
                      </h3>
                      {q.options && (
                        <ul className="ml-4 list-disc list-inside text-sm text-gray-700">
                          {q.options.map((opt, optIdx) => (
                            <li key={optIdx} className="py-0.5">
                              {opt}
                            </li>
                          ))}
                        </ul>
                      )}
                      {q.correct_answer && (
                        <p className="mt-1 text-sm text-[#0F2654]">
                          <strong>Answer:</strong> {q.correct_answer}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 italic">
                    No questions found for this quiz.
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </main>

      <Footer />

      {/* Confirmation Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-lg max-w-sm w-full">
            <h2 className="text-lg font-bold mb-3 text-[#0a3264]">
              Confirm Delete
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              Are you sure you want to delete this quiz? This action cannot be
              undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default function SavedQuizzes() {
  const [savedQuizzes, setSavedQuizzes] = useState<SavedQuiz[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSaved = async () => {
      try {
        const quizzes = await getSavedQuizzes();
        setSavedQuizzes(quizzes);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load saved quizzes.");
      } finally {
        setLoading(false);
      }
    };
    fetchSaved();
  }, []);

  const handleDeleteFromList = (quizId: string) => {
    setSavedQuizzes((prev) => prev.filter((q) => q._id !== quizId));
  };

  return (
    <Suspense
      fallback={<div className="p-8 text-center">Loading saved quizzes...</div>}
    >
      {loading ? (
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0a3264] mx-auto"></div>
        </div>
      ) : (
        <DisplaySavedQuizzesPage
          savedQuizzes={savedQuizzes}
          onDeleteClick={handleDeleteFromList}
        />
      )}
    </Suspense>
  );
}
