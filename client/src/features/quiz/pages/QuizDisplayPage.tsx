"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import {
  CheckButton,
  NewQuizButton,
  QuizAnswerField,
  DownloadQuizButton,
  NavBar,
  Footer,
  ShareButton,
  SaveQuizButton,
} from "@features/quiz/components";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { TokenService } from "@shared/auth/tokenService";
import LiveQuizAccessCodePanel from "@features/live-quiz/components/LiveQuizAccessCodePanel";
import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";

type DocumentContext = {
  sourceDocumentName: string;
  sourceDocumentType: string;
  totalSourceChunks: number;
  retrievedChunks: number;
  sourceCharacters: number;
  ragStrategy: string;
  embeddingCacheHit: boolean;
};

const isAnswerProvided = (answer: string | number | undefined) => {
  if (typeof answer === "number") {
    return true;
  }

  return typeof answer === "string" && answer.trim().length > 0;
};

const QuizDisplayPage: React.FC = () => {
  const searchParams = useSearchParams();
  const isDocumentGenerated = searchParams?.get("generated") === "document";
  const generatedQuizKey = searchParams?.get("generatedQuizKey") || "";
  const savedQuizId = searchParams?.get("savedId") || searchParams?.get("id");
  const canonicalQuizId = searchParams?.get("quizId") || "";
  const questionType = searchParams?.get("questionType") || "multichoice";
  const source = searchParams?.get("source") || "";
  const profession = searchParams?.get("profession") || "general knowledge";
  const customInstruction = searchParams?.get("customInstruction") || "";

  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [userAnswers, setUserAnswers] = useState<(string | number)[]>([]);
  const [isQuizChecked, setIsQuizChecked] = useState<boolean>(false);
  const [quizReport, setQuizReport] = useState<any[]>([]);
  const [quizId, setQuizId] = useState(canonicalQuizId);
  const [quizTitle, setQuizTitle] = useState("");
  const [quizDescription, setQuizDescription] = useState("");
  const [activeQuestionType, setActiveQuestionType] = useState(questionType);
  const [documentContext, setDocumentContext] =
    useState<DocumentContext | null>(null);
  const [liveAccessCode, setLiveAccessCode] = useState("");
  const [liveAccessUrl, setLiveAccessUrl] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const lastFetchKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const fetchKey = JSON.stringify({
      savedQuizId,
      canonicalQuizId,
      questionType,
      source,
      isDocumentGenerated,
      generatedQuizKey,
      profession,
      customInstruction,
    });
    if (lastFetchKeyRef.current === fetchKey) return;
    lastFetchKeyRef.current = fetchKey;

    const fetchQuizQuestions = async () => {
      const applyQuizData = (
        quizData: any,
        options: {
          successMessage?: string;
          clearSavedLocal?: boolean;
        } = {},
      ) => {
        const { successMessage, clearSavedLocal = false } = options;
        const rawQuestions = Array.isArray(quizData?.questions)
          ? quizData.questions
          : Array.isArray(quizData?.quiz_data?.questions)
            ? quizData.quiz_data.questions
            : [];

        if (!rawQuestions.length) {
          throw new Error("No quiz questions found.");
        }

        const resolvedQuestionType =
          quizData?.question_type || quizData?.quiz_type || questionType;
        const normalizedQuestions = rawQuestions.map((q: any) => ({
          ...q,
          answer: q.answer || q.correct_answer,
          question_type: q.question_type || resolvedQuestionType,
        }));
        const resolvedQuizId =
          quizData?.quiz_id || quizData?.id || canonicalQuizId || "";

        setQuizTitle(
          quizData?.title ||
            `${resolvedQuestionType.charAt(0).toUpperCase() + resolvedQuestionType.slice(1)} Quiz`,
        );
        setQuizDescription(quizData?.description || "");
        setActiveQuestionType(resolvedQuestionType);
        setQuizQuestions(normalizedQuestions);
        setUserAnswers(Array(normalizedQuestions.length).fill(""));
        setQuizId(resolvedQuizId);

        if (quizData?.source_document_name) {
          setDocumentContext({
            sourceDocumentName: quizData.source_document_name,
            sourceDocumentType: quizData.source_document_type,
            totalSourceChunks: Number(quizData.total_source_chunks || 0),
            retrievedChunks: Number(quizData.retrieved_chunks || 0),
            sourceCharacters: Number(quizData.source_characters || 0),
            ragStrategy: quizData.rag_strategy || "embedding_mmr",
            embeddingCacheHit: Boolean(quizData.embedding_cache_hit),
          });
        } else {
          setDocumentContext(null);
        }

        if (quizData?.access_code) {
          setLiveAccessCode(quizData.access_code);
          setLiveAccessUrl(
            `${window.location.origin}/quiz-access/${quizData.access_code}`,
          );
        } else {
          setLiveAccessCode("");
          setLiveAccessUrl("");
        }

        if (clearSavedLocal) {
          localStorage.removeItem("saved_quiz_view");
        }
        if (successMessage) {
          toast.success(successMessage);
        }
      };

      try {
        setIsLoading(true);

        const keyedGeneratedQuiz = generatedQuizKey
          ? sessionStorage.getItem(generatedQuizKey)
          : null;

        if (keyedGeneratedQuiz) {
          const parsedGeneratedQuiz = JSON.parse(keyedGeneratedQuiz);
          applyQuizData(
            {
              title:
                parsedGeneratedQuiz?.title ||
                `${profession || "Document"} Quiz`,
              description:
                parsedGeneratedQuiz?.description ||
                customInstruction ||
                "Generated from uploaded learning material.",
              ...parsedGeneratedQuiz,
              quiz_id: parsedGeneratedQuiz?.quiz_id || canonicalQuizId || "",
            },
            {
              successMessage: "Loaded generated quiz successfully!",
            },
          );

          if (TokenService.hasTokens() && parsedGeneratedQuiz?.historyMeta) {
            try {
              if (!parsedGeneratedQuiz.historySaved) {
                const normalizedQuestions = (
                  Array.isArray(parsedGeneratedQuiz?.questions)
                    ? parsedGeneratedQuiz.questions
                    : []
                ).map((q: any) => ({
                  ...q,
                  answer: q.answer || q.correct_answer,
                  question_type: q.question_type || questionType,
                }));
                await saveQuizToHistory(
                  parsedGeneratedQuiz.historyMeta,
                  normalizedQuestions,
                );
                sessionStorage.setItem(
                  generatedQuizKey,
                  JSON.stringify({
                    ...parsedGeneratedQuiz,
                    historySaved: true,
                  }),
                );
              }
            } catch (historyError) {
              console.error(
                "Error saving document quiz history:",
                historyError,
              );
            }
          }

          setIsLoading(false);
          return;
        }

        if (isDocumentGenerated) {
          throw new Error(
            "This document quiz is no longer available in this browser session. Generate it again to continue.",
          );
        }

        if (source === "generated-session") {
          const generatedQuiz = sessionStorage.getItem("generated_quiz_view");
          if (!generatedQuiz) {
            throw new Error("Generated quiz data is unavailable.");
          }
          applyQuizData(JSON.parse(generatedQuiz), {
            successMessage: "Loaded generated quiz successfully!",
          });
          setIsLoading(false);
          return;
        }

        const storedQuiz = localStorage.getItem("saved_quiz_view");
        if (storedQuiz) {
          const parsedQuiz = JSON.parse(storedQuiz);
          applyQuizData(parsedQuiz, {
            successMessage: `Loaded saved quiz: ${parsedQuiz.title || "Quiz"}`,
            clearSavedLocal: true,
          });
          setIsLoading(false);
          return;
        }

        if (savedQuizId) {
          const { data } = await api.get(`/api/saved-quizzes/${savedQuizId}`);
          applyQuizData(data, {
            successMessage: "Loaded saved quiz successfully!",
          });
          setIsLoading(false);
          return;
        }

        if (canonicalQuizId) {
          const { data } = await api.get(`/api/quizzes/${canonicalQuizId}`);
          applyQuizData(data, {
            successMessage: "Loaded quiz successfully!",
          });
          setIsLoading(false);
          return;
        }

        throw new Error("Quiz data is unavailable.");
      } catch (error: any) {
        console.error("Failed to fetch quiz questions:", error);
        toast.error(error.message || "Failed to load quiz questions.");
        setQuizQuestions([]);
        setUserAnswers([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuizQuestions();
  }, [
    savedQuizId,
    canonicalQuizId,
    questionType,
    source,
    isDocumentGenerated,
    generatedQuizKey,
    profession,
    customInstruction,
  ]);

  const handleAnswerChange = (index: number, answer: string | number) => {
    if (isQuizChecked) {
      return;
    }

    const updated = [...userAnswers];
    updated[index] = answer;
    setUserAnswers(updated);
  };

  const checkAnswers = async () => {
    const unansweredQuestions = quizQuestions
      .map((_, index) => index)
      .filter((index) => !isAnswerProvided(userAnswers[index]));

    if (unansweredQuestions.length > 0) {
      const message =
        unansweredQuestions.length === quizQuestions.length
          ? "Answer the quiz before submitting it for grading."
          : `Answer all questions before submitting. ${unansweredQuestions.length} unanswered question${unansweredQuestions.length === 1 ? "" : "s"} left.`;
      toast.error(message);
      return;
    }

    try {
      const payload = quizQuestions.map((q, i) => {
        const correct = q.answer ?? q.correct_answer;
        if (correct === undefined)
          throw new Error(`No answer for ${q.question}`);

        let userAnswer = userAnswers[i];
        let correctAnswer = correct;

        if (q.question_type === "true-false") {
          if (typeof userAnswer === "string") {
            userAnswer = userAnswer.toLowerCase() === "true" ? 1 : 0;
          }
          if (typeof correctAnswer === "string") {
            correctAnswer = correctAnswer.toLowerCase() === "true" ? 1 : 0;
          }
        }

        return {
          question: q.question,
          user_answer: userAnswer,
          correct_answer: correctAnswer,
          question_type: q.question_type || activeQuestionType,
          source: q.source || "unknown",
        };
      });

      const { data: report } = await publicApi.post(
        "/api/grade-answers",
        payload,
      );

      const transformed = report.map((r: any) =>
        r.question_type === "true-false"
          ? {
              ...r,
              user_answer: r.user_answer == 1 ? "true" : "false",
              correct_answer: r.correct_answer == 1 ? "true" : "false",
            }
          : r,
      );

      setQuizReport(transformed);
      setIsQuizChecked(true);
    } catch (err) {
      console.error("Error checking answers:", err);
      toast.error("Failed to grade your quiz. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-[#0a3264]"></div>
      </div>
    );
  }

  if (!quizQuestions.length) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p className="text-gray-600 text-center text-lg">
          No quiz questions found.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-100">
      <NavBar />

      <main className="flex-1 flex justify-center px-4 sm:px-6 md:px-8 py-8">
        <div className="w-full max-w-4xl space-y-10">
          <section className="bg-white shadow rounded-xl px-4 sm:px-6 py-6 sm:py-8 border border-gray-200">
            <h1 className="text-xl sm:text-2xl font-bold text-[#0F2654] mb-6">
              {quizTitle ||
                `${activeQuestionType.charAt(0).toUpperCase() + activeQuestionType.slice(1)} Quiz`}
            </h1>
            {quizDescription && (
              <p className="mb-6 text-sm leading-6 text-slate-600">
                {quizDescription}
              </p>
            )}
            {documentContext && (
              <div className="mb-6 grid gap-3 rounded-xl border border-[#0F2654]/10 bg-[#f8fbff] p-4 text-sm text-slate-700 md:grid-cols-2">
                <p>
                  <span className="font-semibold text-[#0F2654]">Source:</span>{" "}
                  {documentContext.sourceDocumentName}
                </p>
                <p>
                  <span className="font-semibold text-[#0F2654]">Type:</span>{" "}
                  {documentContext.sourceDocumentType.toUpperCase()}
                </p>
                <p>
                  <span className="font-semibold text-[#0F2654]">RAG:</span>{" "}
                  {documentContext.retrievedChunks} of{" "}
                  {documentContext.totalSourceChunks} chunks retrieved
                </p>
                <p>
                  <span className="font-semibold text-[#0F2654]">Cache:</span>{" "}
                  {documentContext.embeddingCacheHit
                    ? "Reused stored document embeddings"
                    : "Generated fresh document embeddings"}
                </p>
                <p>
                  <span className="font-semibold text-[#0F2654]">
                    Strategy:
                  </span>{" "}
                  {documentContext.ragStrategy}
                </p>
                <p>
                  <span className="font-semibold text-[#0F2654]">
                    Content size:
                  </span>{" "}
                  {documentContext.sourceCharacters.toLocaleString()} characters
                </p>
              </div>
            )}

            <div className="space-y-6">
              {quizQuestions.map((q, i) => (
                <div
                  key={i}
                  className="bg-gray-50 p-4 rounded-md border border-gray-200"
                >
                  <h3 className="font-medium text-gray-800 mb-2 text-sm sm:text-base">
                    {i + 1}. {q.question}
                  </h3>
                  <QuizAnswerField
                    questionType={q.question_type}
                    index={i}
                    onAnswerChange={handleAnswerChange}
                    options={q.options || []}
                    value={userAnswers[i]}
                    disabled={isQuizChecked}
                  />
                </div>
              ))}
            </div>

            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-4 sm:space-y-0">
              {!isQuizChecked && <CheckButton onClick={checkAnswers} />}
              <SaveQuizButton quizData={quizQuestions} quizId={quizId} />
              <DownloadQuizButton
                quizId={quizId}
                question_type={activeQuestionType}
                numQuestion={quizQuestions.length}
                quizData={quizQuestions}
                title={quizTitle}
                description={quizDescription}
              />
              <ShareButton quizId={quizId} />
              {isQuizChecked && <NewQuizButton />}
            </div>
            {isQuizChecked && (
              <p className="mt-4 text-sm font-medium text-slate-600">
                Answers are locked after submission and grading.
              </p>
            )}
          </section>

          {liveAccessCode && (
            <section className="rounded-md border border-green-200 bg-green-50 px-4 py-5 shadow-sm">
              <h2 className="text-lg font-bold text-[#0F2654]">
                Live quiz is ready
              </h2>
              <p className="mt-2 text-sm text-slate-700">
                Share this access code with participants.
              </p>
              <p className="mt-3 text-3xl font-bold tracking-widest text-[#0F2654]">
                {liveAccessCode}
              </p>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(liveAccessUrl);
                  toast.success("Live quiz link copied.");
                }}
                className="mt-4 rounded-md border border-[#0F2654] bg-white px-4 py-2 text-sm font-semibold text-[#0F2654] hover:bg-slate-50"
              >
                Copy Live Quiz Link
              </button>
            </section>
          )}

          <LiveQuizAccessCodePanel quizId={quizId} />

          {isQuizChecked && (
            <section className="bg-white shadow rounded-xl px-4 sm:px-6 py-6 sm:py-8 border border-gray-200">
              <h2 className="text-xl sm:text-2xl font-bold text-[#0F2654] mb-4">
                My Quiz Result
              </h2>

              <div className="space-y-4">
                {quizReport.map((r, i) => (
                  <div
                    key={i}
                    className={`p-4 rounded-md border text-sm ${
                      r.is_correct
                        ? "border-green-200 bg-green-50"
                        : "border-red-200 bg-red-50"
                    }`}
                  >
                    <p>
                      <strong>Question:</strong> {r.question}
                    </p>
                    <p>
                      <strong>Your Answer:</strong> {r.user_answer}
                    </p>
                    <p>
                      <strong>Correct:</strong> {r.correct_answer}
                    </p>
                    {r.accuracy_percentage && (
                      <p>
                        <strong>Accuracy:</strong>{" "}
                        {parseFloat(r.accuracy_percentage).toFixed(2)}%
                      </p>
                    )}
                    <p>
                      <strong>Result:</strong> {r.result}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:space-x-4 space-y-4 sm:space-y-0">
                <button className="bg-[#0a3264] hover:bg-[#082952] text-white font-semibold px-4 py-2 rounded-xl shadow-md transition text-sm">
                  Upgrade Plan to Save your Quiz
                </button>
                <NewQuizButton />
              </div>
            </section>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default function DisplayQuiz() {
  return (
    <Suspense fallback={<div>Loading quiz...</div>}>
      <QuizDisplayPage />
    </Suspense>
  );
}
