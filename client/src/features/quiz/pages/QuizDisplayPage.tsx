"use client";

import React, { useState, useEffect, useMemo, useRef, Suspense } from "react";
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
import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { TokenService } from "@shared/auth/tokenService";
import LiveQuizAccessCodePanel from "@features/live-quiz/components/LiveQuizAccessCodePanel";

const isAnswerProvided = (answer: string | number | undefined) => {
  if (typeof answer === "number") {
    return true;
  }

  return typeof answer === "string" && answer.trim().length > 0;
};

const QuizDisplayPage: React.FC = () => {
  const searchParams = useSearchParams();
  const savedQuizId = searchParams?.get("savedId") || searchParams?.get("id");
  const canonicalQuizId = searchParams?.get("quizId") || "";
  const questionType = searchParams?.get("questionType") || "multichoice";
  const numQuestions = Number(searchParams?.get("numQuestions")) || 1;
  const profession = searchParams?.get("profession") || "general knowledge";
  const difficultyLevel = searchParams?.get("difficultyLevel") || "easy";
  const audienceType = searchParams?.get("audienceType") || "students";
  const customInstruction = searchParams?.get("customInstruction") || "";
  const token = searchParams?.get("token") || "";
  const liveQuizRequested = searchParams?.get("liveQuiz") === "true";
  const liveDurationMinutes =
    Number(searchParams?.get("liveDurationMinutes")) || 20;
  const liveAccessExpiresAt = searchParams?.get("liveAccessExpiresAt") || "";
  const participantAccessModeParam = searchParams?.get("participantAccessMode");
  const participantAccessMode: "public" | "restricted" | "invited_only" =
    participantAccessModeParam === "restricted" ||
    participantAccessModeParam === "invited_only"
      ? participantAccessModeParam
      : "public";
  const invitedEmailsParam = searchParams?.get("invitedEmails") || "";
  const invitedEmails = useMemo(
    () =>
      invitedEmailsParam
        .split(",")
        .map((email) => email.trim().toLowerCase())
        .filter(Boolean),
    [invitedEmailsParam],
  );
  const sendEmailInvitations =
    searchParams?.get("sendEmailInvitations") === "true";

  const [quizQuestions, setQuizQuestions] = useState<any[]>([]);
  const [userAnswers, setUserAnswers] = useState<(string | number)[]>([]);
  const [isQuizChecked, setIsQuizChecked] = useState<boolean>(false);
  const [quizReport, setQuizReport] = useState<any[]>([]);
  const [quizId, setQuizId] = useState(canonicalQuizId);
  const [quizTitle, setQuizTitle] = useState("");
  const [quizDescription, setQuizDescription] = useState("");
  const [liveAccessCode, setLiveAccessCode] = useState("");
  const [liveAccessUrl, setLiveAccessUrl] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const fetchQuizQuestions = async () => {
      try {
        setIsLoading(true);
        let questions: any[] = [];
        let resolvedQuizId = "";

        // ✅ Step 1: Check if a saved quiz was passed via localStorage
        const storedQuiz = localStorage.getItem("saved_quiz_view");

        if (storedQuiz) {
          const parsedQuiz = JSON.parse(storedQuiz);
          const storedQuestions = Array.isArray(parsedQuiz?.questions)
            ? parsedQuiz.questions
            : Array.isArray(parsedQuiz?.quiz_data?.questions)
              ? parsedQuiz.quiz_data.questions
              : [];

          if (storedQuestions.length > 0) {
            const resolvedStoredQuizId =
              parsedQuiz?.quiz_id || canonicalQuizId || "";
            setQuizTitle(
              parsedQuiz?.title ||
                `${parsedQuiz?.question_type || questionType} Quiz`,
            );
            setQuizDescription(parsedQuiz?.description || "");
            const normalizedQuestions = storedQuestions.map((q: any) => ({
              ...q,
              answer: q.answer || q.correct_answer,
              question_type: q.question_type || questionType,
            }));
            setQuizQuestions(normalizedQuestions);
            setUserAnswers(Array(normalizedQuestions.length).fill(""));
            if (resolvedStoredQuizId) {
              setQuizId(resolvedStoredQuizId);
            }
            toast.success(`Loaded saved quiz: ${parsedQuiz.title}`);
            localStorage.removeItem("saved_quiz_view");
            setIsLoading(false);
            return;
          }
        }

        // ✅ Step 2: If there’s a savedQuizId in URL, fetch from API
        if (savedQuizId) {
          const { data } = await api.get(`/api/saved-quizzes/${savedQuizId}`);

          if (!data || !data.questions || data.questions.length === 0) {
            throw new Error("No questions found for this saved quiz.");
          }

          questions = data.questions.map((q: any) => ({
            ...q,
            answer: q.answer || q.correct_answer,
            question_type: q.question_type || questionType,
          }));
          setQuizTitle(
            data.title || `${data.question_type || questionType} Quiz`,
          );
          setQuizDescription(data.description || "");
          const resolvedSavedQuizId = data.quiz_id || canonicalQuizId || "";
          setQuizId(resolvedSavedQuizId);
          resolvedQuizId = resolvedSavedQuizId;
          toast.success("Loaded saved quiz successfully!");
        } else {
          // ✅ Step 3: Fallback — generate a new quiz
          const basePayload = {
            question_type: questionType,
            num_questions: numQuestions,
            profession,
            difficulty_level: difficultyLevel,
            audience_type: audienceType,
            custom_instruction: customInstruction,
            token,
            live_quiz_enabled: liveQuizRequested,
            time_limit_minutes: liveQuizRequested
              ? liveDurationMinutes
              : undefined,
            access_code_expires_at: liveQuizRequested
              ? liveAccessExpiresAt
              : undefined,
            participant_access_mode: liveQuizRequested
              ? participantAccessMode
              : undefined,
            invited_emails: liveQuizRequested ? invitedEmails : undefined,
            send_email_invitations: liveQuizRequested
              ? sendEmailInvitations
              : undefined,
          };

          const client =
            liveQuizRequested || TokenService.hasTokens() ? api : publicApi;
          const { data } = await client.post("/api/get-questions", basePayload);

          if (data?.quiz_id && !data?.ai_down) {
            setQuizId(data.quiz_id);
            resolvedQuizId = data.quiz_id;
          }
          if (data?.access_code) {
            setLiveAccessCode(data.access_code);
            setLiveAccessUrl(
              `${window.location.origin}/quiz-access/${data.access_code}`,
            );
            toast.success("Live quiz access code generated!");
          }
          if (data?.ai_down) {
            toast.error(data.notification_message || "AI model unavailable.", {
              duration: 4000,
            });
            setQuizId("");
            resolvedQuizId = "";
          }

          questions =
            data?.questions?.map((q: any) => ({
              ...q,
              question_type: q.question_type || questionType,
            })) || [];
          setQuizTitle(
            `${profession || questionType.charAt(0).toUpperCase() + questionType.slice(1)} Quiz`,
          );
          setQuizDescription(
            customInstruction ||
              `A ${difficultyLevel} ${questionType} quiz for ${audienceType}.`,
          );
          if (!Array.isArray(questions) || questions.length === 0) {
            throw new Error("No quiz questions returned.");
          }

          toast.success("Generated new quiz successfully!");
        }

        setQuizQuestions(questions);
        setUserAnswers(Array(questions.length).fill(""));

        if (!savedQuizId && TokenService.hasTokens()) {
          try {
            await saveQuizToHistory(
              {
                quiz_id: resolvedQuizId || undefined,
                question_type: questionType,
                num_questions: numQuestions,
                difficulty_level: difficultyLevel,
                profession: profession,
                audience_type: audienceType,
                custom_instruction: customInstruction,
              },
              questions,
            );
          } catch (err) {
            console.error("Error saving quiz history:", err);
          }
        }
      } catch (error: any) {
        console.error("❌ Failed to fetch quiz questions:", error);
        toast.error(error.message || "Failed to fetch quiz questions.");
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
    numQuestions,
    profession,
    difficultyLevel,
    audienceType,
    customInstruction,
    token,
    liveQuizRequested,
    liveDurationMinutes,
    liveAccessExpiresAt,
    participantAccessMode,
    invitedEmails,
    sendEmailInvitations,
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
          question_type: q.question_type || questionType,
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

      // History is saved on generation to avoid duplicate entries.
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
          {/* Quiz Questions */}
          <section className="bg-white shadow rounded-xl px-4 sm:px-6 py-6 sm:py-8 border border-gray-200">
            <h1 className="text-xl sm:text-2xl font-bold text-[#0F2654] mb-6">
              {`${questionType.charAt(0).toUpperCase() + questionType.slice(1)} Quiz`}
            </h1>

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
                question_type={questionType}
                numQuestion={numQuestions}
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

          {/* Quiz Results */}
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
