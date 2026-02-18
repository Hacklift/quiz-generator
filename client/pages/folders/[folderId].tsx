"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import {
  getFolderById,
  removeQuizFromFolder,
} from "../../lib/functions/folders";
import MoveQuizModal from "../../components/home/folders/MoveQuizModal";
import ConfirmDeleteModal from "../../components/home/folders/ConfirmDeleteModal";
import { FaArrowLeft, FaEllipsisV } from "react-icons/fa";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";
import { useAuth } from "../../contexts/authContext";
import RequireAuth from "../../components/auth/RequireAuth";

const FolderView = () => {
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
        toast.error("Failed to load folder");
      } finally {
        setLoading(false);
      }
    };
    fetchFolder();
  }, [folderId, user]);

  const handleDeleteQuizConfirmed = async (quizId: string) => {
    try {
      await removeQuizFromFolder(folderId as string, quizId);
      toast.success("Quiz deleted successfully");
      setFolder((prev: any) =>
        prev
          ? {
              ...prev,
              quizzes: prev.quizzes.filter((q: any) => q._id !== quizId),
            }
          : prev,
      );
    } catch (err) {
      console.error(err);
      toast.error("Error deleting quiz");
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
    router.push("/quiz_display");
  };

  const formatDate = (date: string) => {
    if (!date) return "Date unavailable";
    const parsed = new Date(date);
    return isNaN(parsed.getTime())
      ? "Date unavailable"
      : parsed.toLocaleDateString();
  };

  const getQuizTitle = (quiz: any) => quiz.title || "Untitled Quiz";
  const getQuizQuestions = (quiz: any) =>
    quiz.questions || quiz.quiz_data?.questions || [];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <NavBar />
      <RequireAuth
        title="Folder Access"
        description="Sign in to view and manage quizzes in this folder."
      >
        {loading ? (
          <div className="flex justify-center items-center h-screen text-gray-600">
            <p>Loading folder...</p>
          </div>
        ) : !folder ? (
          <div className="flex justify-center items-center h-screen text-gray-500">
            <p>Folder not found.</p>
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
                {folder.quizzes?.length || 0} quizzes • Created on{" "}
                {formatDate(folder.created_at)}
              </p>
            </header>

            <main className="flex-1 p-6 flex flex-col items-center gap-6">
              {folder.quizzes.length === 0 ? (
                <div className="w-full text-center text-gray-500">
                  <p>No quizzes in this folder.</p>
                </div>
              ) : (
                folder.quizzes.map((quiz: any) => (
                  <div
                    key={quiz._id}
                    className="quiz-card relative border rounded-2xl p-4 shadow-sm bg-white hover:shadow-md transition-all flex flex-col justify-between w-full max-w-3xl group"
                  >
                    <div>
                      <h3 className="text-navy-800 font-semibold mb-1 truncate">
                        {getQuizTitle(quiz)}
                      </h3>
                      <p className="text-sm text-gray-500 mb-2">
                        Added on {formatDate(quiz.added_on || quiz.created_at)}
                      </p>

                      <div className="text-sm text-gray-600 mt-2 bg-gray-50 p-2 rounded-md border">
                        <p>
                          <strong>Type:</strong>{" "}
                          {quiz.question_type ||
                            quiz.quiz_data?.question_type ||
                            "N/A"}
                        </p>
                        <p>
                          <strong>Questions:</strong>{" "}
                          {getQuizQuestions(quiz).length}
                        </p>
                        {getQuizQuestions(quiz).length > 0 && (
                          <div className="mt-2">
                            <p className="font-medium text-gray-700 mb-1">
                              Questions Preview:
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
                            openMenuId === quiz._id ? null : quiz._id,
                          )
                        }
                        className="p-2 hover:bg-gray-100 rounded-full"
                      >
                        <FaEllipsisV className="text-gray-600" />
                      </button>

                      {openMenuId === quiz._id && (
                        <div className="absolute right-0 mt-2 w-36 bg-white border border-gray-200 rounded-lg shadow-lg z-10 flex flex-col">
                          <button
                            onClick={() => handleViewQuiz(quiz)}
                            className="px-3 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-t-lg"
                          >
                            View Quiz
                          </button>
                          <button
                            onClick={() => handleMoveQuiz(quiz)}
                            className="px-3 py-2 text-sm text-navy-700 bg-blue-100 hover:bg-blue-200"
                          >
                            Move
                          </button>
                          <button
                            onClick={() => handleDeleteQuizClick(quiz._id)}
                            className="px-3 py-2 text-sm text-red-600 bg-red-100 hover:bg-red-200 rounded-b-lg"
                          >
                            Delete
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
