"use client";

import { useState, useEffect } from "react";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import { useAuth } from "@features/auth/context/authContext";
import { useRouter } from "next/navigation";
import { TokenService } from "@shared/auth/tokenService";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";

type ApiErrorLike = {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
};

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
      } catch (e: unknown) {
        const typedError = e as ApiErrorLike & { response?: { status?: number } };
        if (typedError?.response?.status === 404) {
          return;
        }
        console.warn("Error fetching user token:", typedError);
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
      sessionStorage.setItem("generated_quiz_view", JSON.stringify(generatedQuizView));

      const queryParams = new URLSearchParams({
        questionType,
        ...(canonicalQuizId ? { quizId: canonicalQuizId } : { source: "generated-session" }),
      }).toString();

      router.push(`/quiz_display?${queryParams}`);
    } catch (error: unknown) {
      const typedError = error as ApiErrorLike;
      setErrorMessage(
        typedError?.response?.data?.detail ||
          typedError?.message ||
          "Failed to generate quiz. Please try again.",
      );
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
