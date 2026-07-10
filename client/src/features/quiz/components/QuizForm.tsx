"use client";

import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import {
  DocumentQuizResponse,
  generateDocumentQuiz,
} from "@features/quiz/api/documentQuizApi";
import { useAuth } from "@features/auth/context/authContext";
import { useRouter } from "next/navigation";
import { TokenService } from "@shared/auth/tokenService";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";

const DOCUMENT_UPLOAD_MAX_BYTES = 10 * 1024 * 1024;
const DOCUMENT_TEXT_MAX_CHARS = 50_000;
const SUPPORTED_DOCUMENT_EXTENSIONS = new Set(["pdf", "docx", "txt"]);

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes.toLocaleString()} B`;
  }

  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

export default function QuizForm() {
  const [generationMode, setGenerationMode] = useState<"document" | "topic">(
    "topic",
  );
  const [profession, setProfession] = useState("");
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentInputMode, setDocumentInputMode] = useState<
    "paste" | "upload"
  >("upload");
  const [documentText, setDocumentText] = useState("");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [audienceType, setAudienceType] = useState("");
  const [customInstruction, setCustomInstruction] = useState("");
  const [numQuestions, setNumQuestions] = useState(1);
  const [questionType, setQuestionType] = useState("multichoice");
  const [difficultyLevel, setDifficultyLevel] = useState("easy");
  const [token, setToken] = useState("");
  const [previousToken, setPreviousToken] = useState("");
  const [enableLiveQuiz, setEnableLiveQuiz] = useState(false);
  const [liveDurationMinutes, setLiveDurationMinutes] = useState(20);
  const [liveAccessExpiresAt, setLiveAccessExpiresAt] = useState(() => {
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
    tomorrow.setMinutes(tomorrow.getMinutes() - tomorrow.getTimezoneOffset());
    return tomorrow.toISOString().slice(0, 16);
  });
  const [participantAccessMode, setParticipantAccessMode] = useState<
    "public" | "restricted" | "invited_only"
  >("public");
  const [invitedEmailsText, setInvitedEmailsText] = useState("");
  const [sendEmailInvitations, setSendEmailInvitations] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const router = useRouter();
  const { user, isAuthenticated } = useAuth();

  const handleDocumentFileChange = (file: File | null) => {
    if (!file) {
      setDocumentFile(null);
      return;
    }

    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !SUPPORTED_DOCUMENT_EXTENSIONS.has(extension)) {
      setDocumentFile(null);
      setErrorMessage("Please upload a PDF, DOCX, or TXT file.");
      toast.error("Unsupported file type. Upload PDF, DOCX, or TXT.");
      return;
    }

    if (file.size <= 0) {
      setDocumentFile(null);
      setErrorMessage("The selected file is empty.");
      toast.error("The selected file is empty.");
      return;
    }

    if (file.size > DOCUMENT_UPLOAD_MAX_BYTES) {
      setDocumentFile(null);
      setErrorMessage(
        `The selected file is too large. Maximum size is ${DOCUMENT_UPLOAD_MAX_BYTES.toLocaleString()} bytes.`,
      );
      toast.error(
        `File too large. Maximum size is ${formatBytes(DOCUMENT_UPLOAD_MAX_BYTES)}.`,
      );
      return;
    }

    setDocumentFile(file);
    setErrorMessage("");
    toast.success(
      `${file.name} uploaded successfully. Ready for quiz generation.`,
    );
  };

  useEffect(() => {
    if (user === undefined) return;

    if (!user || !isAuthenticated) {
      setPreviousToken("");
      return;
    }

    const savedLocal = sessionStorage.getItem("user_api_token");
    if (savedLocal) setPreviousToken(savedLocal);

    const loadFromBackend = async () => {
      try {
        const res = await api.get("/api/user/token", {
          validateStatus: (status) => status === 200 || status === 404,
        });

        if (res.status === 404) {
          return;
        }

        if (res.data?.token) {
          setPreviousToken(res.data.token);
          sessionStorage.setItem("user_api_token", res.data.token);
        }
      } catch (e: any) {
        if (e?.response?.status === 404) {
          return;
        }
        console.warn("Error fetching user token:", e);
      }
    };

    loadFromBackend();
  }, [user, isAuthenticated]);

  const handleGenerateQuiz = async () => {
    if (generationMode === "topic" && !profession) {
      setErrorMessage("Please enter a profession or topic for your quiz.");
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "upload" &&
      !documentFile
    ) {
      setErrorMessage("Please upload a PDF, DOCX, or TXT file.");
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "paste" &&
      !documentText.trim()
    ) {
      setErrorMessage("Please paste the learning material.");
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "paste" &&
      documentText.length > DOCUMENT_TEXT_MAX_CHARS
    ) {
      setErrorMessage(
        `Pasted text is too long. Maximum length is ${DOCUMENT_TEXT_MAX_CHARS.toLocaleString()} characters.`,
      );
      return;
    }

    if (!questionType) {
      setErrorMessage("Please select a question type.");
      return;
    }

    if (!numQuestions || numQuestions <= 0) {
      setErrorMessage("Please enter a valid number of questions.");
      return;
    }

    if (enableLiveQuiz && (!user || !isAuthenticated)) {
      setErrorMessage("Please log in to generate a live quiz access code.");
      return;
    }

    if (enableLiveQuiz && liveDurationMinutes <= 0) {
      setErrorMessage("Please enter a valid live quiz duration.");
      return;
    }

    if (
      enableLiveQuiz &&
      new Date(liveAccessExpiresAt).getTime() <= Date.now()
    ) {
      setErrorMessage("Please choose a future access code expiration time.");
      return;
    }

    const invitedEmails = invitedEmailsText
      .split(/[\s,;]+/)
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean);

    if (
      enableLiveQuiz &&
      (participantAccessMode === "restricted" ||
        participantAccessMode === "invited_only") &&
      invitedEmails.length === 0
    ) {
      setErrorMessage(
        "Please add at least one invited email for restricted access.",
      );
      return;
    }

    setErrorMessage("");
    setLoading(true);

    try {
      if (user && token.trim()) {
        const accessToken = TokenService.getAccessToken();

        await api.post(
          "/api/user/token",
          { token },
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
            withCredentials: true,
          },
        );

        sessionStorage.setItem("user_api_token", token);
      }

      if (generationMode === "document") {
        const payload = new FormData();
        payload.append("question_type", questionType);
        payload.append("num_questions", numQuestions.toString());
        payload.append("difficulty_level", difficultyLevel);
        payload.append("audience_type", audienceType || "students");
        payload.append("custom_instruction", customInstruction);
        payload.append("token", token);
        payload.append("document_title", documentTitle);
        payload.append("focus_topic", profession);
        payload.append("live_quiz_enabled", enableLiveQuiz ? "true" : "false");

        if (enableLiveQuiz) {
          payload.append("time_limit_minutes", liveDurationMinutes.toString());
          payload.append(
            "access_code_expires_at",
            new Date(liveAccessExpiresAt).toISOString(),
          );
        }

        if (documentInputMode === "upload" && documentFile) {
          payload.append("document_file", documentFile);
        } else {
          payload.append("document_text", documentText);
        }

        const response: DocumentQuizResponse = await generateDocumentQuiz(
          payload,
          {
            authenticated: enableLiveQuiz || isAuthenticated,
          },
        );
        const generatedQuizKey = response.quiz_id
          ? `generated_quiz_view:${response.quiz_id}`
          : `generated_quiz_view:${Date.now()}`;

        sessionStorage.setItem(
          generatedQuizKey,
          JSON.stringify({
            ...response,
            historyMeta: {
              quiz_id: response.quiz_id,
              question_type: questionType,
              num_questions: numQuestions,
              difficulty_level: difficultyLevel,
              profession: response.title,
              audience_type: audienceType || "students",
              custom_instruction:
                customInstruction ||
                `Generated from ${response.source_document_type.toUpperCase()} material.`,
            },
          }),
        );

        const queryParams = new URLSearchParams({
          generated: "document",
          generatedQuizKey,
          questionType,
          numQuestions: numQuestions.toString(),
          profession: response.title,
          customInstruction:
            customInstruction ||
            `Generated from ${response.source_document_type.toUpperCase()} material.`,
          audienceType: audienceType || "students",
          difficultyLevel,
        }).toString();

        if (response.quiz_id) {
          const enrichedParams = new URLSearchParams(queryParams);
          enrichedParams.set("quizId", response.quiz_id);
          router.push(`/quiz_display?${enrichedParams.toString()}`);
          return;
        }

        router.push(`/quiz_display?${queryParams}`);
        return;
      }

      const payload = {
        question_type: questionType,
        num_questions: numQuestions,
        profession,
        custom_instruction: customInstruction,
        audience_type: audienceType,
        difficulty_level: difficultyLevel,
        token,
        live_quiz_enabled: enableLiveQuiz,
        time_limit_minutes: enableLiveQuiz ? liveDurationMinutes : undefined,
        access_code_expires_at: enableLiveQuiz
          ? new Date(liveAccessExpiresAt).toISOString()
          : undefined,
        participant_access_mode: enableLiveQuiz ? participantAccessMode : undefined,
        invited_emails: enableLiveQuiz ? invitedEmails : undefined,
        send_email_invitations: enableLiveQuiz
          ? sendEmailInvitations
          : undefined,
      };

      const client = enableLiveQuiz || TokenService.hasTokens() ? api : publicApi;
      const { data } = await client.post("/api/get-questions", payload);
      const questions = Array.isArray(data?.questions) ? data.questions : [];
      if (!questions.length) {
        throw new Error("No quiz questions returned.");
      }

      let canonicalQuizId = data?.quiz_id || "";
      if (TokenService.hasTokens()) {
        try {
          const historyResponse = await saveQuizToHistory(
            {
              quiz_id: canonicalQuizId || undefined,
              question_type: questionType,
              num_questions: numQuestions,
              difficulty_level: difficultyLevel,
              profession,
              audience_type: audienceType,
              custom_instruction: customInstruction,
            },
            questions,
          );
          canonicalQuizId = canonicalQuizId || historyResponse?.data?.quiz_id || "";
        } catch (historyError) {
          console.error("Error saving quiz history:", historyError);
        }
      }

      const generatedQuizView = {
        id: canonicalQuizId || undefined,
        quiz_id: canonicalQuizId || undefined,
        title: profession || `${questionType} Quiz`,
        description:
          customInstruction ||
          `A ${difficultyLevel} ${questionType} quiz for ${audienceType || "students"}.`,
        question_type: questionType,
        questions,
        live_quiz_enabled: data?.live_quiz_enabled,
        access_code: data?.access_code,
        time_limit_minutes: data?.time_limit_minutes,
        access_code_expires_at: data?.access_code_expires_at,
      };
      sessionStorage.setItem(
        "generated_quiz_view",
        JSON.stringify(generatedQuizView),
      );

      const queryParams = new URLSearchParams({
        questionType,
        numQuestions: numQuestions.toString(),
        profession,
        customInstruction,
        audienceType,
        difficultyLevel,
        token,
        liveQuiz: enableLiveQuiz ? "true" : "false",
        liveDurationMinutes: liveDurationMinutes.toString(),
        liveAccessExpiresAt: enableLiveQuiz
          ? new Date(liveAccessExpiresAt).toISOString()
          : "",
        participantAccessMode: enableLiveQuiz
          ? participantAccessMode
          : "public",
        invitedEmails: enableLiveQuiz ? invitedEmails.join(",") : "",
        sendEmailInvitations:
          enableLiveQuiz && sendEmailInvitations ? "true" : "false",
        source: "generated-session",
        ...(canonicalQuizId ? { quizId: canonicalQuizId } : {}),
      }).toString();

      router.push(`/quiz_display?${queryParams}`);
    } catch (error: any) {
      const detail =
        error?.response?.data?.detail ||
        error?.message ||
        "Failed to generate quiz. Please try again.";
      setErrorMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-[#f7f8fa] rounded-xl p-10 shadow-lg">
      <form onSubmit={(e) => e.preventDefault()}>
        <QuizGenerationSection
          generationMode={generationMode}
          setGenerationMode={setGenerationMode}
          profession={profession}
          setProfession={setProfession}
          documentTitle={documentTitle}
          setDocumentTitle={setDocumentTitle}
          documentInputMode={documentInputMode}
          setDocumentInputMode={setDocumentInputMode}
          documentText={documentText}
          setDocumentText={setDocumentText}
          documentFileName={documentFile?.name || ""}
          documentFileSizeBytes={documentFile?.size || 0}
          documentUploadMaxBytes={DOCUMENT_UPLOAD_MAX_BYTES}
          documentTextLimit={DOCUMENT_TEXT_MAX_CHARS}
          onDocumentFileChange={handleDocumentFileChange}
          audienceType={audienceType}
          setAudienceType={setAudienceType}
          customInstruction={customInstruction}
          setCustomInstruction={setCustomInstruction}
          numQuestions={numQuestions}
          setNumQuestions={setNumQuestions}
          questionType={questionType}
          setQuestionType={setQuestionType}
          difficultyLevel={difficultyLevel}
          setDifficultyLevel={setDifficultyLevel}
          token={token}
          setToken={setToken}
          previousToken={previousToken}
        />

        <section className="mt-6 rounded-md border border-slate-200 bg-white p-5">
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={enableLiveQuiz}
              onChange={(event) => setEnableLiveQuiz(event.target.checked)}
              className="mt-1 h-4 w-4 accent-[#0F2654]"
            />
            <span>
              <span className="block text-sm font-semibold text-[#2C3E50]">
                Generate this quiz as a live session
              </span>
              <span className="mt-1 block text-xs text-gray-500">
                A shareable access code will be generated as soon as the quiz is
                created.
              </span>
            </span>
          </label>

          {enableLiveQuiz && (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-semibold text-[#2C3E50]">
                Quiz duration minutes
                <input
                  type="number"
                  min={1}
                  max={1440}
                  value={liveDurationMinutes}
                  onChange={(event) =>
                    setLiveDurationMinutes(Number(event.target.value))
                  }
                  className="mt-2 w-full rounded-md border border-gray-300 px-4 py-2 focus:outline-none focus:ring focus:ring-blue-500"
                />
              </label>
              <label className="block text-sm font-semibold text-[#2C3E50]">
                Access code expiration
                <input
                  type="datetime-local"
                  value={liveAccessExpiresAt}
                  onChange={(event) =>
                    setLiveAccessExpiresAt(event.target.value)
                  }
                  className="mt-2 w-full rounded-md border border-gray-300 px-4 py-2 focus:outline-none focus:ring focus:ring-blue-500"
                />
              </label>
              <label className="block text-sm font-semibold text-[#2C3E50]">
                Participant access
                <select
                  value={participantAccessMode}
                  onChange={(event) =>
                    setParticipantAccessMode(
                      event.target.value as
                        | "public"
                        | "restricted"
                        | "invited_only",
                    )
                  }
                  className="mt-2 w-full rounded-md border border-gray-300 px-4 py-2 focus:outline-none focus:ring focus:ring-blue-500"
                >
                  <option value="public">Public link</option>
                  <option value="restricted">Invited emails only</option>
                  <option value="invited_only">
                    Invited emails only (strict)
                  </option>
                </select>
              </label>
              <label className="block text-sm font-semibold text-[#2C3E50] md:col-span-2">
                Invitation emails
                <textarea
                  value={invitedEmailsText}
                  onChange={(event) => setInvitedEmailsText(event.target.value)}
                  placeholder="ada@example.com, grace@example.com"
                  rows={3}
                  className="mt-2 w-full rounded-md border border-gray-300 px-4 py-2 focus:outline-none focus:ring focus:ring-blue-500"
                />
              </label>
              <label className="flex items-center gap-2 text-sm font-semibold text-[#2C3E50]">
                <input
                  type="checkbox"
                  checked={sendEmailInvitations}
                  onChange={(event) =>
                    setSendEmailInvitations(event.target.checked)
                  }
                  className="h-4 w-4 accent-[#0F2654]"
                />
                Send invitation emails
              </label>
            </div>
          )}
        </section>

        {errorMessage && (
          <p className="text-red-500 mb-4 font-medium">{errorMessage}</p>
        )}

        <GenerateButton onClick={handleGenerateQuiz} loading={loading} />
      </form>
    </div>
  );
}
