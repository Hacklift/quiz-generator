"use client";
import { useTranslation } from "react-i18next";

import React, { useEffect, useRef, useState, Suspense } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import {
  getSavedQuizzes,
  deleteSavedQuiz,
  renameSavedQuiz,
} from "@features/saved-quizzes/api/savedQuizApi";
import {
  getUserFolders,
  createFolder,
  addQuizToFolder,
} from "@features/folders/api/foldersApi";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { useAuth } from "@features/auth/context/authContext";
import RequireAuth from "@features/auth/components/RequireAuth";
import { useTerms } from "@features/persona/hooks/useTerms";

interface QuizQuestion {
  question: string;
  options?: string[];
  correct_answer?: string;
}

interface SavedQuiz {
  id?: string;
  _id?: string;
  quiz_id?: string;
  title: string;
  created_at: string;
  questions?: QuizQuestion[];
  question_type?: string;
}

interface Folder {
  id?: string;
  _id?: string;
  name: string;
  created_at: string;
}

const getSavedQuizId = (quiz: Partial<SavedQuiz>) => quiz._id || quiz.id || "";
const getFolderId = (folder: Partial<Folder>) => folder._id || folder.id || "";

const AddToFolderModal = ({
  isOpen,
  onClose,
  selectedQuizIds,
}: {
  isOpen: boolean;
  onClose: () => void;
  selectedQuizIds: string[];
}) => {
  const { t: uiText, i18n } = useTranslation("ui");

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
        toast.error(uiText("mb44e9fbeb8bfb4ed"));
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
      toast.error(uiText("m2451b55f7853f4ac"));
      return;
    }

    try {
      let targetFolderId = selectedFolderId;

      if (!targetFolderId && newFolderName) {
        const newFolder = await createFolder({ name: newFolderName });
        targetFolderId = getFolderId(newFolder);
      }

      for (const quizId of selectedQuizIds) {
        await addQuizToFolder(targetFolderId!, { id: quizId });
      }

      toast.success(uiText("m988a8c43ec0e7b46"));
      onClose();
    } catch (err) {
      console.error(err);
      toast.error(uiText("m6888b6aa42200909"));
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-xl shadow-lg max-w-md w-full">
        <h2 className="text-xl font-bold text-[#0F2654] mb-4">
          {uiText("mf64faf41096abe41")}
        </h2>

        {loading ? (
          <p className="text-gray-600 text-sm">{uiText("mf553c87b32d744c0")}</p>
        ) : (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {uiText("m5dad087aa168df6d")}
              </label>
              {folders.length === 0 ? (
                <p className="text-gray-500 text-sm italic">
                  {uiText("m0d21e8017cdf93eb")}
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
                            (folder) =>
                              getFolderId(folder) === selectedFolderId,
                          )?.name
                        : uiText("m74bed7b49a5d8b99")}
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
                          key={getFolderId(folder)}
                          type="button"
                          role="option"
                          aria-selected={
                            getFolderId(folder) === selectedFolderId
                          }
                          onClick={() => {
                            setSelectedFolderId(getFolderId(folder));
                            setFolderMenuOpen(false);
                          }}
                          className={`w-full px-4 py-2 text-left text-sm ${
                            getFolderId(folder) === selectedFolderId
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
                {uiText("mee932d21bf636b4f")}
              </label>
              <input
                type="text"
                placeholder={uiText("m9e2c1ffcf0963a0d")}
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
                {uiText("m19766ed6ccb2f4a3")}
              </button>
              <button
                onClick={handleAddToFolder}
                className="px-4 py-2 rounded-lg bg-[#0a3264] text-white hover:bg-[#082952]"
              >
                {uiText("m1509f561f2416598")}
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
  onRenameClick: (quizId: string, title: string) => void;
  token: string;
}> = ({ savedQuizzes, onDeleteClick, onRenameClick, token }) => {
  const { t: uiText, i18n } = useTranslation("ui");

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [selectedQuizIds, setSelectedQuizIds] = useState<string[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [renameTarget, setRenameTarget] = useState<SavedQuiz | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const router = useRouter();
  const t = useTerms();

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
      toast.success(uiText("m866be84df2395a81"));
      onDeleteClick(confirmDeleteId);
      setConfirmDeleteId(null);
    } catch (err) {
      console.error(err);
      toast.error(uiText("m20786e658137366e"));
    }
  };

  const handleViewQuiz = (quiz: SavedQuiz) => {
    if (!token) {
      toast.error(uiText("m0225db4f8b665edb"));
      return;
    }

    localStorage.setItem("saved_quiz_view", JSON.stringify(quiz));
    router.push(
      `/quiz_display?savedId=${getSavedQuizId(quiz)}&quizId=${quiz.quiz_id || getSavedQuizId(quiz)}&questionType=${quiz.question_type || "multichoice"}`,
    );
  };

  const handleRenameQuiz = async () => {
    if (!renameTarget) return;
    if (!renameTitle.trim()) {
      toast.error(uiText("m97208a101194c78e"));
      return;
    }

    try {
      setIsRenaming(true);
      const savedQuizId = getSavedQuizId(renameTarget);
      await renameSavedQuiz(savedQuizId, renameTitle.trim(), token);
      toast.success(uiText("m26dfb060d1d36d75"));
      onRenameClick(savedQuizId, renameTitle.trim());
    } catch (err) {
      console.error(err);
      toast.error(uiText("mb1b01916ab11244a"));
    } finally {
      setIsRenaming(false);
      setRenameTarget(null);
      setRenameTitle("");
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />
      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
              {uiText("mce0983f3577f5ce9", { value0: t("quiz", "plural") })}
            </h1>

            {selectedQuizIds.length > 0 && (
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-[#0a3264] text-white px-4 py-2 rounded-lg text-sm hover:bg-[#082952]"
              >
                {uiText("m3e84bd33e9ee0e4b", {
                  value0: selectedQuizIds.length,
                })}
              </button>
            )}
          </div>

          {savedQuizzes.length === 0 ? (
            <p className="text-center text-gray-600">
              {uiText("m2fa492d6198bfb12", { value0: t("quiz", "plural") })}
            </p>
          ) : (
            savedQuizzes.map((quiz) => (
              <div
                key={getSavedQuizId(quiz)}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-200 relative"
              >
                <input
                  type="checkbox"
                  className="absolute top-4 left-4 w-4 h-4"
                  checked={selectedQuizIds.includes(getSavedQuizId(quiz))}
                  onChange={() => toggleSelectQuiz(getSavedQuizId(quiz))}
                />

                <div className="ml-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <p className="text-sm text-gray-500 mb-2">
                        {uiText("m34dcaa4300172f3b", {
                          value0: quiz.created_at
                            ? new Date(quiz.created_at).toLocaleString(
                                i18n.language,
                              )
                            : uiText("mad224bb89c8a3fb6"),
                        })}
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
                        onClick={() => {
                          setRenameTarget(quiz);
                          setRenameTitle(quiz.title);
                        }}
                        className="text-sm text-[#0a3264] hover:text-[#082952] font-semibold"
                      >
                        {uiText("m3064d79a295cefe4")}
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(getSavedQuizId(quiz))}
                        className="text-sm text-red-600 hover:text-red-800 font-semibold"
                      >
                        {uiText("me2d0a54968ead24e")}
                      </button>
                      <button
                        onClick={() => handleViewQuiz(quiz)}
                        className="text-sm bg-[#0a3264] hover:bg-[#082952] text-white px-3 py-1 rounded-lg font-semibold"
                      >
                        {uiText("m515f6a0d4288e0d7")}
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
              {uiText("ma7f54311a3e625f5")}
            </h2>
            <p className="text-sm text-gray-600 mb-6">
              {uiText("m3f560f9a50bf7e09")}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
              >
                {uiText("m19766ed6ccb2f4a3")}
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
              >
                {uiText("me2d0a54968ead24e")}
              </button>
            </div>
          </div>
        </div>
      )}

      {renameTarget && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-lg max-w-sm w-full">
            <h2 className="text-lg font-bold mb-3 text-[#0a3264]">
              {uiText("me1d64a3c005aa092")}
            </h2>
            <input
              type="text"
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4"
              placeholder={uiText("mbbd849696814d82d")}
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setRenameTarget(null);
                  setRenameTitle("");
                }}
                className="px-4 py-2 rounded-lg border text-gray-600 hover:bg-gray-100"
              >
                {uiText("m19766ed6ccb2f4a3")}
              </button>
              <button
                onClick={handleRenameQuiz}
                disabled={isRenaming}
                className="px-4 py-2 rounded-lg bg-[#0a3264] text-white hover:bg-[#082952] disabled:opacity-50"
              >
                {isRenaming
                  ? uiText("m75595af6803156eb")
                  : uiText("m1509f561f2416598")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default function SavedQuizzes() {
  const { t: uiText, i18n } = useTranslation("ui");

  const { token, isAuthenticated } = useAuth();
  const [savedQuizzes, setSavedQuizzes] = useState<SavedQuiz[]>([]);
  const [loading, setLoading] = useState(true);

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
        toast.error(uiText("m587b4d0dc657a578"));
      } finally {
        setLoading(false);
      }
    };
    fetchSaved();
  }, [token, isAuthenticated]);

  return (
    <RequireAuth
      title={uiText("mcdd228db96c869e0")}
      description={uiText("mc52bfe0923d3225b")}
    >
      <Suspense
        fallback={
          <div className="p-8 text-center">{uiText("m766b350530eb64da")}</div>
        }
      >
        {loading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0a3264] mx-auto"></div>
          </div>
        ) : (
          <DisplaySavedQuizzesPage
            savedQuizzes={savedQuizzes}
            onDeleteClick={(id) =>
              setSavedQuizzes((prev) =>
                prev.filter((q) => getSavedQuizId(q) !== id),
              )
            }
            onRenameClick={(id, title) =>
              setSavedQuizzes((prev) =>
                prev.map((quiz) =>
                  getSavedQuizId(quiz) === id ? { ...quiz, title } : quiz,
                ),
              )
            }
            token={token!}
          />
        )}
      </Suspense>
    </RequireAuth>
  );
}
