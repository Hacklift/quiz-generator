"use client";

import { useState, useEffect } from "react";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import { useAuth } from "@features/auth/context/authContext";
import { useRouter } from "next/navigation";
import { TokenService } from "@shared/auth/tokenService";
import { api } from "@shared/api/http";

export default function QuizForm() {
  const [profession, setProfession] = useState("");
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
    if (!profession) {
      setErrorMessage("Please enter a profession or topic for your quiz.");
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

    if (enableLiveQuiz && new Date(liveAccessExpiresAt).getTime() <= Date.now()) {
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
      setErrorMessage("Please add at least one invited email for restricted access.");
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
        participantAccessMode: enableLiveQuiz ? participantAccessMode : "public",
        invitedEmails: enableLiveQuiz ? invitedEmails.join(",") : "",
        sendEmailInvitations:
          enableLiveQuiz && sendEmailInvitations ? "true" : "false",
      }).toString();

      router.push(`/quiz_display?${queryParams}`);
    } catch (error) {
      setErrorMessage("Failed to generate quiz. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-[#f7f8fa] rounded-xl p-10 shadow-lg">
      <form onSubmit={(e) => e.preventDefault()}>
        <QuizGenerationSection
          profession={profession}
          setProfession={setProfession}
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
                  <option value="invited_only">Invited emails only (strict)</option>
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
