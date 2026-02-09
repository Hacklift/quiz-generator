"use client";

import React, { useEffect, useRef, useState, Suspense } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import {
  getSavedQuizzes,
  deleteSavedQuiz,
  saveQuiz,
} from "../../lib/functions/savedQuiz";
import {
  getUserFolders,
  createFolder,
  addQuizToFolder,
} from "../../lib/functions/folders";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";
import { useAuth } from "../../contexts/authContext";
import SignInModal from "../../components/auth/SignInModal";

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

interface Folder {
  _id: string;
  name: string;
  created_at: string;
}

const AddToFolderModal = ({
  isOpen,
  onClose,
  selectedQuizIds,
}: {
  isOpen: boolean;
  onClose: () => void;
  selectedQuizIds: string[];
}) => {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [newFolderName, setNewFolderName] = useState("");
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [folderMenuOpen, setFolderMenuOpen] = useState(false);
  const folderMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const fetchFolders = async () => {
      try {
        const res = await getUserFolders();
        setFolders(res);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load folders");
      } finally {
        setLoading(false);
      }
    };
    fetchFolders();
  }, [isOpen]);

  useEffect(() => {
    if (!folderMenuOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        folderMenuRef.current &&
        !folderMenuRef.current.contains(event.target as Node)
      ) {
        setFolderMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [folderMenuOpen]);

  const handleAddToFolder = async () => {
    if (!selectedFolderId && !newFolderName) {
      toast.error("Please select or create a folder.");
      return;
    }

    try {
      let targetFolderId = selectedFolderId;

      if (!targetFolderId && newFolderName) {
        const newFolder = await createFolder({ name: newFolderName });
        targetFolderId = newFolder._id;
      }

      for (const quizId of selectedQuizIds) {
        await addQuizToFolder(targetFolderId!, { _id: quizId });
      }

      toast.success("Quiz(es) added to folder successfully!");
      onClose();
    } catch (err) {
      console.error(err);
      toast.error("Failed to add quiz(es) to folder.");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl shadow-lg max-w-md w-full">
        <h2 className="text-xl font-bold text-[#0F2654] mb-4">
          Add Quiz to Folder
        </h2>

        {loading ? (
          <p className="text-gray-600 text-sm">Loading folders...</p>
        ) : (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Choose an existing folder:
              </label>
              {folders.length === 0 ? (
                <p className="text-gray-500 text-sm italic">
                  No folders available.
                </p>
              ) : (
                <div className="relative" ref={folderMenuRef}>
                  <button
                    type="button"
                    onClick={() => setFolderMenuOpen((prev) => !prev)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-left bg-white text-[#2C3E50] focus:outline-none focus:ring focus:ring-blue-500 flex items-center justify-between"
                    aria-haspopup="listbox"
                    aria-expanded={folderMenuOpen}
                  >
                    <span>
                      {selectedFolderId
                        ? folders.find(
                            (folder) => folder._id === selectedFolderId,
                          )?.name
                        : "Select a folder"}
                    </span>
                    <svg
                      className={`h-4 w-4 text-[#0F2654] transition-transform ${
                        folderMenuOpen ? "rotate-180" : ""
                      }`}
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                  {folderMenuOpen && (
                    <div
                      className="absolute left-0 right-0 mt-1 rounded-md border border-[#0F2654]/20 bg-white shadow-lg z-20 max-h-56 overflow-auto"
                      role="listbox"
                    >
                      {folders.map((folder) => (
                        <button
                          key={folder._id}
                          type="button"
                          role="option"
                          aria-selected={folder._id === selectedFolderId}
                          onClick={() => {
                            setSelectedFolderId(folder._id);
                            setFolderMenuOpen(false);
                          }}
                          className={`w-full px-4 py-2 text-left text-sm ${
                            folder._id === selectedFolderId
                              ? "bg-[#0F2654] text-white"
                              : "text-[#2C3E50] hover:bg-[#0F2654]/10"
                          }`}
                        >
                          {folder.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Or create a new folder:
              </label>
              <input
                type="text"
                placeholder="Enter new folder name"
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleAddToFolder}
                className="px-4 py-2 rounded-lg bg-[#0a3264] text-white hover:bg-[#082952]"
              >
                Save
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const DisplaySavedQuizzesPage: React.FC<{
  savedQuizzes: SavedQuiz[];
  onDeleteClick: (quizId: string) => void;
  token: string;
}> = ({ savedQuizzes, onDeleteClick, token }) => {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [selectedQuizIds, setSelectedQuizIds] = useState<string[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const router = useRouter();

  const toggleSelectQuiz = (quizId: string) => {
    setSelectedQuizIds((prev) =>
      prev.includes(quizId)
        ? prev.filter((id) => id !== quizId)
        : [...prev, quizId],
    );
  };

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return;
    try {
      await deleteSavedQuiz(confirmDeleteId, token);
      toast.success("Quiz deleted successfully!");
      onDeleteClick(confirmDeleteId);
      setConfirmDeleteId(null);
    } catch (err) {
      console.error(err);
      toast.error("Failed to delete quiz");
    }
  };

  const handleViewQuiz = async (quiz: SavedQuiz) => {
    if (!token) {
      toast.error("Authentication required to view this quiz.");
      return;
    }

    const questionType = quiz.question_type || "unknown-type";

    if (quiz.questions && quiz.questions.length > 0) {
      try {
        await saveQuiz(quiz.title, questionType, quiz.questions, token);
      } catch (err) {
        console.error("Failed to save quiz:", err);
        toast.error("Failed to load quiz.");
      }
    }

    router.push(`/quiz_display?id=${quiz._id}`, { scroll: true });
    localStorage.setItem("saved_quiz_view", JSON.stringify(quiz));
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />
      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
              Saved Quizzes
            </h1>

            {selectedQuizIds.length > 0 && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-[#0a3264] text-white px-4 py-2 rounded-lg text-sm hover:bg-[#082952]"
              >
                Add to Folder ({selectedQuizIds.length})
              </button>
            )}
          </div>

          {savedQuizzes.length === 0 ? (
            <p className="text-center text-gray-600">
              You haven’t saved any quizzes yet.
            </p>
          ) : (
            savedQuizzes.map((quiz) => (
              <div
                key={quiz._id}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-200 relative"
              >
                <input
                  type="checkbox"
                  className="absolute top-4 left-4 w-4 h-4"
                  checked={selectedQuizIds.includes(quiz._id)}
                  onChange={() => toggleSelectQuiz(quiz._id)}
                />

                <div className="ml-6">
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

                      {quiz.questions && quiz.questions.length > 0 && (
                        <div className="mt-4 space-y-3">
                          {quiz.questions.map((q, idx) => (
                            <div
                              key={idx}
                              className="p-3 border rounded-lg bg-gray-50"
                            >
                              <p className="font-medium">
                                {idx + 1}. {q.question}
                              </p>
                              {q.options && q.options.length > 0 && (
                                <ul className="list-disc list-inside mt-1 text-gray-700">
                                  {q.options.map((opt, i) => (
                                    <li key={i}>{opt}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
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
                </div>
              </div>
            ))
          )}
        </div>
      </main>
      <Footer />

      <AddToFolderModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        selectedQuizIds={selectedQuizIds}
      />

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
  const { user, token, isAuthenticated, isLoading } = useAuth();
  const [savedQuizzes, setSavedQuizzes] = useState<SavedQuiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      return;
    }
    const fetchSaved = async () => {
      try {
        const quizzes = await getSavedQuizzes(token);
        setSavedQuizzes(quizzes);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load saved quizzes.");
      } finally {
        setLoading(false);
      }
    };
    fetchSaved();
  }, [token, isAuthenticated]);

  if (!isAuthenticated && !isLoading) {
    return (
      <>
        <div className="flex flex-col items-center justify-center min-h-screen text-center text-gray-700">
          <h1 className="text-2xl font-bold mb-2">Authentication Required</h1>
          <p>
            Please{" "}
            <span
              onClick={() => setIsLoginOpen(true)}
              className="text-blue-600 underline cursor-pointer"
            >
              log in
            </span>{" "}
            to view your saved quizzes.
          </p>
        </div>

        <SignInModal
          isOpen={isLoginOpen}
          onClose={() => setIsLoginOpen(false)}
          switchToSignUp={() => {}}
        />
      </>
    );
  }

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
          onDeleteClick={(id) =>
            setSavedQuizzes((prev) => prev.filter((q) => q._id !== id))
          }
          token={token!}
        />
      )}
    </Suspense>
  );
}
