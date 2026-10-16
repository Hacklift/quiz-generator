"use client";
import { useTranslation } from "react-i18next";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import {
  getFolderById,
  removeQuizFromFolder,
} from "@features/folders/api/foldersApi";
import MoveQuizModal from "@features/folders/components/MoveQuizModal";
import ConfirmDeleteModal from "@features/folders/components/ConfirmDeleteModal";
import { FaArrowLeft, FaEllipsisV } from "react-icons/fa";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import { useAuth } from "@features/auth/context/authContext";
import RequireAuth from "@features/auth/components/RequireAuth";

const getFolderItemId = (quiz: any) => quiz?.id || "";

const FolderView = () => {
  const { t: uiText, i18n } = useTranslation("ui");

  const router = useRouter();
  const { folderId } = router.query;
  const { user, isAuthenticated } = useAuth();

  const [folder, setFolder] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [moveModalOpen, setMoveModalOpen] = useState(false);
  const [selectedQuiz, setSelectedQuiz] = useState<any>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [quizToDelete, setQuizToDelete] = useState<string | null>(null);

  const refreshFolderData = async () => {
    if (!isAuthenticated || !folderId || !user) return;
    try {
      const res = await getFolderById(folderId as string);
      setFolder(res);
    } catch (err) {
      console.error("Failed to fetch folder:", err);
    }
  };

  useEffect(() => {
    if (!isAuthenticated || !folderId || !user) return;
    const fetchFolder = async () => {
      try {
        setLoading(true);
        const res = await getFolderById(folderId as string);
        setFolder(res);
      } catch (err) {
        console.error(err);
        toast.error(uiText("mb0cb71cf9ee4b0a5"));
      } finally {
        setLoading(false);
      }
    };
    fetchFolder();
  }, [folderId, isAuthenticated, user]);

  const handleDeleteQuizConfirmed = async (quizId: string) => {
    try {
      await removeQuizFromFolder(folderId as string, quizId);
      toast.success(uiText("m8b0925714fce10e7"));
      setFolder((prev: any) =>
        prev
          ? {
              ...prev,
              quizzes: prev.quizzes.filter(
                (q: any) => getFolderItemId(q) !== quizId,
              ),
            }
          : prev,
      );
    } catch (err) {
      console.error(err);
      toast.error(uiText("mc32bc95b9897c6fc"));
    }
  };

  const handleDeleteQuizClick = (quizId: string) => {
    setQuizToDelete(quizId);
    setConfirmModalOpen(true);
  };

  const handleMoveQuiz = (quiz: any) => {
    setSelectedQuiz(quiz);
    setMoveModalOpen(true);
  };

  const handleViewQuiz = (quiz: any) => {
    localStorage.setItem("saved_quiz_view", JSON.stringify(quiz));
    router.push(
      `/quiz_display?quizId=${quiz.quiz_id || ""}&questionType=${quiz.question_type || quiz.quiz_data?.question_type || "multichoice"}`,
    );
  };

  const formatDate = (date: string) => {
    if (!date) return uiText("mad224bb89c8a3fb6");
    const parsed = new Date(date);
    return isNaN(parsed.getTime())
      ? uiText("mad224bb89c8a3fb6")
      : parsed.toLocaleDateString(i18n.language);
  };

  const getQuizTitle = (quiz: any) => quiz.title || uiText("m96c2c6ca09471b4d");
  const getQuizQuestions = (quiz: any) =>
    quiz.questions || quiz.quiz_data?.questions || [];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <NavBar />
      <RequireAuth
        title={uiText("m4f6dd3d9aafb5968")}
        description={uiText("m5400755a4196bbff")}
      >
        {loading ? (
          <div className="flex justify-center items-center h-screen text-gray-600">
            <p>{uiText("me54f895605402f41")}</p>
          </div>
        ) : !folder ? (
          <div className="flex justify-center items-center h-screen text-gray-500">
            <p>{uiText("mccbf07f84d310412")}</p>
          </div>
        ) : (
          <>
            <div className="px-6 mt-4">
              <button
                onClick={() => router.push("/folders")}
                className="text-sm bg-[#0a3264] hover:bg-[#082952] text-white px-7 py-1 rounded-lg font-semibold"
              >
                <FaArrowLeft />
              </button>
            </div>

            <header className="p-6 flex flex-col items-center text-center">
              <div className="text-4xl mb-2">📁</div>
              <h2 className="text-2xl font-bold text-navy-800 mb-1">
                {folder.name}
              </h2>
              <p className="text-sm text-gray-500">
                {uiText("mb6cc77afda6a9d8f", {
                  value0: folder.quizzes?.length || 0,
                  value1: formatDate(folder.created_at),
                })}
              </p>
            </header>

            <main className="flex-1 p-6 flex flex-col items-center gap-6">
              {folder.quizzes.length === 0 ? (
                <div className="w-full text-center text-gray-500">
                  <p>{uiText("mbf32802309ef0625")}</p>
                </div>
              ) : (
                folder.quizzes.map((quiz: any) => (
                  <div
                    key={getFolderItemId(quiz)}
                    className="quiz-card relative border rounded-2xl p-4 shadow-sm bg-white hover:shadow-md transition-all flex flex-col justify-between w-full max-w-3xl group"
                  >
                    <div>
                      <h3 className="text-navy-800 font-semibold mb-1 truncate">
                        {getQuizTitle(quiz)}
                      </h3>
                      <p className="text-sm text-gray-500 mb-2">
                        {uiText("me17e189f84ccfd31", {
                          value0: formatDate(quiz.added_on || quiz.created_at),
                        })}
                      </p>

                      <div className="text-sm text-gray-600 mt-2 bg-gray-50 p-2 rounded-md border">
                        <p>
                          <strong>{uiText("m6cc5ad2e47e3be35")}</strong>{" "}
                          {quiz.question_type ||
                            quiz.quiz_data?.question_type ||
                            "N/A"}
                        </p>
                        <p>
                          <strong>{uiText("m80f86d1e313fb622")}</strong>{" "}
                          {getQuizQuestions(quiz).length}
                        </p>
                        {getQuizQuestions(quiz).length > 0 && (
                          <div className="mt-2">
                            <p className="font-medium text-gray-700 mb-1">
                              {uiText("mc1c4721dd52b6c4b")}
                            </p>
                            {getQuizQuestions(quiz).map(
                              (q: any, idx: number) => (
                                <div key={idx} className="mb-2">
                                  <p className="italic text-gray-500">
                                    {idx + 1}. {q.question}
                                  </p>
                                  {q.options && (
                                    <ul className="ml-4 list-disc text-gray-600">
                                      {q.options.map(
                                        (opt: string, i: number) => (
                                          <li key={i}>{opt}</li>
                                        ),
                                      )}
                                    </ul>
                                  )}
                                </div>
                              ),
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() =>
                          setOpenMenuId(
                            openMenuId === getFolderItemId(quiz)
                              ? null
                              : getFolderItemId(quiz),
                          )
                        }
                        className="p-2 hover:bg-gray-100 rounded-full"
                      >
                        <FaEllipsisV className="text-gray-600" />
                      </button>

                      {openMenuId === getFolderItemId(quiz) && (
                        <div className="absolute right-0 mt-2 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-10 flex flex-col">
                          <button
                            onClick={() => handleViewQuiz(quiz)}
                            className="px-3 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-t-lg"
                          >
                            {uiText("m515f6a0d4288e0d7")}
                          </button>
                          <button
                            onClick={() => handleMoveQuiz(quiz)}
                            className="px-3 py-2 text-sm text-navy-700 bg-blue-100 hover:bg-blue-200"
                          >
                            {uiText("m6ecc3df6bffdd06c")}
                          </button>
                          <button
                            onClick={() =>
                              handleDeleteQuizClick(getFolderItemId(quiz))
                            }
                            className="px-3 py-2 text-sm text-red-600 bg-red-100 hover:bg-red-200 rounded-b-lg"
                          >
                            {uiText("me2d0a54968ead24e")}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </main>

            <MoveQuizModal
              isOpen={moveModalOpen}
              onClose={() => setMoveModalOpen(false)}
              quiz={selectedQuiz}
              sourceFolderId={folderId as string}
              onQuizMoved={refreshFolderData}
            />

            {confirmModalOpen && quizToDelete && (
              <ConfirmDeleteModal
                selectedItems={[quizToDelete]}
                type="quiz"
                onClose={() => {
                  setConfirmModalOpen(false);
                  setQuizToDelete(null);
                }}
                onDeleted={(deletedIds: string[]) => {
                  handleDeleteQuizConfirmed(deletedIds[0]);
                  setConfirmModalOpen(false);
                  setQuizToDelete(null);
                }}
              />
            )}
          </>
        )}
      </RequireAuth>

      <Footer />
    </div>
  );
};

export default FolderView;
