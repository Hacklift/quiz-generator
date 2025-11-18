"use client";

import React, { Suspense, useEffect, useState } from "react";
import { getUserQuizHistory } from "../../lib/functions/getUserQuizHistory";
import { useAuth } from "../../contexts/authContext";
import NavBar from "../../components/home/NavBar";
import Footer from "../../components/home/Footer";

const transformQuizHistory = (quizHistory: any[]) => {
  if (!quizHistory || quizHistory.length === 0) return [];

  return quizHistory.map((quizItem: any, quizIndex: number) => {
    const createdAt = quizItem.created_at
      ? new Date(quizItem.created_at).toLocaleString()
      : "Unknown date";

    const listedQuizQuestions = quizItem.questions.map(
      (quizQuestion: any, qIndex: number) => {
        let optionsList: JSX.Element | null = null;

        if (quizQuestion.options) {
          optionsList = (
            <ul className="ml-4 list-disc list-inside text-sm text-gray-700">
              {quizQuestion.options.map((option: string, optIdx: number) => (
                <li key={optIdx} className="py-0.5">
                  {option}
                </li>
              ))}
            </ul>
          );
        }

        return (
          <div key={qIndex} className="mb-4">
            <h3 className="font-semibold text-gray-800 text-base sm:text-lg mb-1">
              {qIndex + 1}. {quizQuestion.question}
            </h3>

            {optionsList}

            <p className="mt-1 text-sm text-[#0F2654]">
              <strong>Answer:</strong> {quizQuestion.answer}
            </p>
          </div>
        );
      },
    );

    return (
      <div key={quizIndex}>
        <hr className="border-gray-300 my-4" />
        <p className="text-sm text-gray-500 mb-3">Generated on: {createdAt}</p>
        <div>{listedQuizQuestions}</div>
      </div>
    );
  });
};

const DisplayQuizHistoryPage = ({
  quizHistory,
  isLoggedIn,
  openLoginModal,
}: {
  quizHistory: JSX.Element[];
  isLoggedIn: boolean;
  openLoginModal: () => void;
}) => {
  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 px-4 sm:px-6 md:px-8 py-8">
        <div className="max-w-4xl mx-auto space-y-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-[#0F2654]">
            Quiz History
          </h1>

          {!isLoggedIn ? (
            <p className="text-center text-gray-600">
              You must{" "}
              <span
                onClick={openLoginModal}
                className="text-blue-600 cursor-pointer hover:underline"
              >
                sign in
              </span>{" "}
              to view your quiz history.
            </p>
          ) : quizHistory.length === 0 ? (
            <p className="text-center text-gray-600">
              No quiz history available.
            </p>
          ) : (
            quizHistory.map((quizElement, idx) => (
              <div
                key={idx}
                className="bg-white p-6 rounded-xl shadow-md border border-gray-200"
              >
                {quizElement}
              </div>
            ))
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default function DisplayQuizHistory({
  openLoginModal,
}: {
  openLoginModal: () => void;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const [quizHistory, setQuizHistory] = useState<JSX.Element[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const fetchQuizHistory = async () => {
      try {
        const rawHistory: any[] = (await getUserQuizHistory()) ?? [];
        const transformed = transformQuizHistory(rawHistory);
        setQuizHistory(transformed);
      } catch (error) {
        console.error("Failed to fetch quiz history:", error);
        setQuizHistory([]);
      } finally {
        setLoading(false);
      }
    };

    fetchQuizHistory();
  }, [isAuthenticated, isLoading]);

  if (isLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0F2654]"></div>
      </div>
    );
  }

  return (
    <Suspense
      fallback={<div className="p-8 text-center">Loading quiz history...</div>}
    >
      <DisplayQuizHistoryPage
        quizHistory={quizHistory}
        isLoggedIn={isAuthenticated}
        openLoginModal={openLoginModal}
      />
    </Suspense>
  );
}
