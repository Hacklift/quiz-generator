"use client";
import { useTranslation } from "react-i18next";

import {
  useState,
  useEffect,
  useRef,
  useId,
  type Dispatch,
  type SetStateAction,
} from "react";
import toast from "react-hot-toast";
import GenerateButton from "./GenerateButton";
import QuizGenerationSection from "./QuizGenerationSection";
import {
  DocumentQuizResponse,
  generateDocumentQuiz,
} from "@features/quiz/api/documentQuizApi";
import { useAuth } from "@features/auth/context/authContext";
import { useRouter, useSearchParams } from "next/navigation";
import { TokenService } from "@shared/auth/tokenService";
import { api } from "@shared/api/http";
import publicApi from "@shared/api/publicHttp";
import { saveQuizToHistory } from "@features/quiz-history/api/saveQuizToHistoryApi";
import PersonaBadge from "@features/persona/components/PersonaBadge";
import { usePersona } from "@features/persona/context/personaContext";
import { useTerms } from "@features/persona/hooks/useTerms";
import { useLocale } from "@features/locale/context/localeContext";
import LanguagePicker from "@features/locale/components/LanguagePicker";
import { LOCALE_DISPLAY_NAMES } from "@shared/config/locale";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";
import { readStoredPersonaTopic } from "@features/persona/lib/personaStorage";
import {
  getPersonaGenerationDefaults,
  getUserTypeDefinition,
  type PersonaGenerationDefaults,
  type PersonaUserType,
} from "@shared/config/persona";

type ApiErrorLike = {
  response?: {
    data?: {
      detail?: string | { code?: string; provider?: string; message?: string };
    };
  };
  message?: string;
};

const DOCUMENT_UPLOAD_MAX_BYTES = 10 * 1024 * 1024;
const DOCUMENT_TEXT_MAX_CHARS = 50_000;
const SUPPORTED_DOCUMENT_EXTENSIONS = new Set(["pdf", "docx", "txt"]);
const parsedQuizGenerationMaxQuestions = Number(
  process.env.NEXT_PUBLIC_QUIZ_GENERATION_MAX_QUESTIONS,
);
const QUIZ_GENERATION_MAX_QUESTIONS =
  Number.isInteger(parsedQuizGenerationMaxQuestions) &&
  parsedQuizGenerationMaxQuestions > 0
    ? parsedQuizGenerationMaxQuestions
    : 10;
const QUERY_AUDIENCE_MAX_CHARS = 80;
const DIFFICULTY_LEVELS = new Set(["easy", "medium", "hard"]);
const QUESTION_TYPES = new Set([
  "multichoice",
  "true-false",
  "short-answer",
  "open-ended",
]);
const PERSONA_GENERATION_PRESETS: Partial<
  Record<PersonaUserType, Record<string, PersonaGenerationDefaults>>
> = {
  teacher: {
    "class-quiz": {
      audienceType: "students",
      customInstruction:
        "Create a marking-ready in-class quiz with clear answer options and an answer key.",
      difficultyLevel: "easy",
      numQuestions: 10,
      questionType: "multichoice",
    },
    "homework-check": {
      audienceType: "students",
      customInstruction:
        "Create a homework check with concise questions and answer explanations for rapid marking.",
      difficultyLevel: "medium",
      numQuestions: 10,
      questionType: "short-answer",
    },
    "exam-revision": {
      audienceType: "students",
      customInstruction:
        "Create an exam revision quiz that mixes recall and application across the topic.",
      difficultyLevel: "hard",
      numQuestions: 10,
      questionType: "multichoice",
    },
  },
  lecturer: {
    "lecture-recap": {
      audienceType: "undergraduates",
      customInstruction:
        "Create a concise post-lecture recap that checks retention of the key concepts covered in the lecture.",
      difficultyLevel: "medium",
      numQuestions: 10,
      questionType: "multichoice",
    },
    "seminar-prep": {
      audienceType: "undergraduates",
      customInstruction:
        "Create a low-stakes seminar preparation quiz that checks understanding of the assigned reading.",
      difficultyLevel: "medium",
      numQuestions: 10,
      questionType: "multichoice",
    },
  },
};

function queryDifficultyOrDefault(
  value: string | null | undefined,
  fallback: PersonaGenerationDefaults["difficultyLevel"],
) {
  return value && DIFFICULTY_LEVELS.has(value) ? value : fallback;
}

function queryQuestionTypeOrDefault(
  value: string | null | undefined,
  fallback: PersonaGenerationDefaults["questionType"],
) {
  return value && QUESTION_TYPES.has(value) ? value : fallback;
}

function queryQuestionCountOrDefault(
  value: string | null | undefined,
  fallback: number,
) {
  const safeFallback = Math.min(QUIZ_GENERATION_MAX_QUESTIONS, fallback);
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return safeFallback;
  }

  return Math.min(QUIZ_GENERATION_MAX_QUESTIONS, parsed);
}

function queryAudienceOrDefault(
  value: string | null | undefined,
  fallback: string,
) {
  const trimmed = value?.trim();
  return trimmed ? trimmed.slice(0, QUERY_AUDIENCE_MAX_CHARS) : fallback;
}

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
  const { t: uiText } = useTranslation("ui");

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
  const [aiProvider, setAiProvider] = useState<"huggingface" | "gemini">(
    "huggingface",
  );
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
  const { locale } = useLocale();
  const [quizLocaleOverride, setQuizLocaleOverride] = useState<string | null>(
    null,
  );
  const quizLocale = quizLocaleOverride ?? locale;
  const [languageExpanded, setLanguageExpanded] = useState(false);
  const languageOptionsId = useId();
  const [allowSampleFallback, setAllowSampleFallback] = useState(false);
  const sampleAvailable =
    ["en", "es", "fr"].includes(quizLocale) && numQuestions <= 10;
  const { roles } = usePersonaCopy();
  const appliedPresetRef = useRef<string | null>(null);
  const touchedGenerationFieldsRef = useRef({
    audienceType: false,
    customInstruction: false,
    difficultyLevel: false,
    numQuestions: false,
    questionType: false,
  });

  const markGenerationFieldTouched =
    <T,>(
      field: keyof typeof touchedGenerationFieldsRef.current,
      setter: Dispatch<SetStateAction<T>>,
    ) =>
    (value: SetStateAction<T>) => {
      touchedGenerationFieldsRef.current[field] = true;
      setter(value);
    };

  const handleDocumentFileChange = (file: File | null) => {
    if (!file) {
      setDocumentFile(null);
      return;
    }

    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !SUPPORTED_DOCUMENT_EXTENSIONS.has(extension)) {
      setDocumentFile(null);
      setErrorMessage(uiText("m173a2e1479fc5e3c"));
      toast.error(uiText("mb8a3c5e48f9a324e"));
      return;
    }

    if (file.size <= 0) {
      setDocumentFile(null);
      setErrorMessage(uiText("m42eb27c3baf606ac"));
      toast.error(uiText("m42eb27c3baf606ac"));
      return;
    }

    if (file.size > DOCUMENT_UPLOAD_MAX_BYTES) {
      setDocumentFile(null);
      setErrorMessage(
        uiText("ma761247cd1d6b805", {
          value0: DOCUMENT_UPLOAD_MAX_BYTES.toLocaleString(),
        }),
      );
      toast.error(
        uiText("m3212b912177d8b53", {
          value0: formatBytes(DOCUMENT_UPLOAD_MAX_BYTES),
        }),
      );
      return;
    }

    setDocumentFile(file);
    setErrorMessage("");
    toast.success(uiText("mb22b6c8a5a7dd202", { value0: file.name }));
  };

  // PersonaProvider resolves profile > URL query > localStorage, so persona
  // entry points and post-auth carry-through use the same app-wide rule.
  const searchParams = useSearchParams();
  const { persona } = usePersona();
  const t = useTerms();
  const personaTopicPlaceholder = persona
    ? roles[persona.userType].defaultTopic
    : "Enter the concept/context here";

  useEffect(() => {
    const defaultTopic = persona
      ? getUserTypeDefinition(persona.userType).defaultTopic
      : "";
    const personaTopic =
      searchParams?.get("topic") || readStoredPersonaTopic(persona);
    if (personaTopic && personaTopic !== defaultTopic) {
      setGenerationMode("topic");
      setProfession((current) => current || personaTopic);
    }
  }, [persona, searchParams]);

  // #133: Apply persona-aware generation defaults on form load.
  useEffect(() => {
    if (!persona) return;

    const defaults = getPersonaGenerationDefaults(persona.userType);
    if (!defaults) return;

    const queryAudience = searchParams?.get("audienceType");
    const queryCustomInstruction = searchParams?.get("customInstruction");
    const queryDifficulty = searchParams?.get("difficultyLevel");
    const queryNumQuestions = searchParams?.get("numQuestions");
    const queryQuestionType = searchParams?.get("questionType");
    const presetKey = searchParams?.get("preset") || "";
    const hasApplicablePreset = Boolean(
      PERSONA_GENERATION_PRESETS[persona.userType]?.[presetKey],
    );
    const touched = touchedGenerationFieldsRef.current;

    if (!hasApplicablePreset && !touched.audienceType) {
      setAudienceType(
        queryAudienceOrDefault(queryAudience, defaults.audienceType),
      );
    }
    if (!hasApplicablePreset && !touched.customInstruction) {
      setCustomInstruction(
        queryCustomInstruction || defaults.customInstruction,
      );
    }
    if (!hasApplicablePreset && !touched.difficultyLevel) {
      setDifficultyLevel(
        queryDifficultyOrDefault(queryDifficulty, defaults.difficultyLevel),
      );
    }
    if (!hasApplicablePreset && !touched.numQuestions) {
      setNumQuestions(
        queryQuestionCountOrDefault(queryNumQuestions, defaults.numQuestions),
      );
    }
    if (!hasApplicablePreset && !touched.questionType) {
      setQuestionType(
        queryQuestionTypeOrDefault(queryQuestionType, defaults.questionType),
      );
    }
  }, [persona, searchParams]);

  useEffect(() => {
    const presetKey = searchParams?.get("preset") || "";
    const userType = persona?.userType;
    const preset = userType
      ? PERSONA_GENERATION_PRESETS[userType]?.[presetKey]
      : undefined;

    if (!preset || !userType) {
      return;
    }
    const presetIdentity = `${userType}:${presetKey}`;
    if (appliedPresetRef.current === presetIdentity) {
      return;
    }

    const queryAudience = searchParams?.get("audienceType");
    const queryCustomInstruction = searchParams?.get("customInstruction");
    const queryDifficulty = searchParams?.get("difficultyLevel");
    const queryNumQuestions = searchParams?.get("numQuestions");
    const queryQuestionType = searchParams?.get("questionType");
    const touched = touchedGenerationFieldsRef.current;

    appliedPresetRef.current = presetIdentity;
    setGenerationMode("topic");
    if (!touched.audienceType) {
      setAudienceType(
        queryAudienceOrDefault(queryAudience, preset.audienceType),
      );
    }
    if (!touched.customInstruction) {
      setCustomInstruction(queryCustomInstruction || preset.customInstruction);
    }
    if (!touched.difficultyLevel) {
      setDifficultyLevel(
        queryDifficultyOrDefault(queryDifficulty, preset.difficultyLevel),
      );
    }
    if (!touched.numQuestions) {
      setNumQuestions(
        queryQuestionCountOrDefault(queryNumQuestions, preset.numQuestions),
      );
    }
    if (!touched.questionType) {
      setQuestionType(
        queryQuestionTypeOrDefault(queryQuestionType, preset.questionType),
      );
    }
  }, [persona?.userType, searchParams]);

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
        const typedError = e as ApiErrorLike & {
          response?: { status?: number };
        };
        if (typedError?.response?.status === 404) {
          return;
        }
        console.warn("Error fetching user token:", typedError);
      }
    };

    loadFromBackend();
  }, [user, isAuthenticated]);

  const handleGenerateQuiz = async () => {
    const resolvedAudienceType = audienceType || t("learner", "plural");

    if (generationMode === "topic" && !profession) {
      setErrorMessage(uiText("m227c928826ed8bcb"));
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "upload" &&
      !documentFile
    ) {
      setErrorMessage(uiText("m173a2e1479fc5e3c"));
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "paste" &&
      !documentText.trim()
    ) {
      setErrorMessage(uiText("m2da7107eed1cff79"));
      return;
    }

    if (
      generationMode === "document" &&
      documentInputMode === "paste" &&
      documentText.length > DOCUMENT_TEXT_MAX_CHARS
    ) {
      setErrorMessage(
        uiText("mad55b9bf63883c88", {
          value0: DOCUMENT_TEXT_MAX_CHARS.toLocaleString(),
        }),
      );
      return;
    }

    if (!questionType) {
      setErrorMessage(uiText("mec3eab8cd2416496"));
      return;
    }

    if (!numQuestions || numQuestions <= 0) {
      setErrorMessage(uiText("m73a3247c93fbb9ff"));
      return;
    }

    if (enableLiveQuiz && (!user || !isAuthenticated)) {
      setErrorMessage(uiText("m53cbf34943e51c86"));
      return;
    }

    if (enableLiveQuiz && liveDurationMinutes <= 0) {
      setErrorMessage(uiText("m108c206214c743c4"));
      return;
    }

    if (
      enableLiveQuiz &&
      new Date(liveAccessExpiresAt).getTime() <= Date.now()
    ) {
      setErrorMessage(uiText("mbeb717e219eb1d60"));
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
      setErrorMessage(uiText("ma0d76e1e03a44731"));
      return;
    }

    setErrorMessage("");
    setLoading(true);

    try {
      if (aiProvider === "huggingface" && user && token.trim()) {
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
        payload.append("audience_type", resolvedAudienceType);
        payload.append("custom_instruction", customInstruction);
        payload.append("ai_provider", aiProvider);
        if (aiProvider === "huggingface") payload.append("token", token);
        payload.append("document_title", documentTitle);
        payload.append("focus_topic", profession);
        payload.append("live_quiz_enabled", enableLiveQuiz ? "true" : "false");
        payload.append("content_locale", quizLocale);
        payload.append(
          "allow_fallback",
          String(allowSampleFallback && sampleAvailable),
        );

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
              content_locale: response.content_locale || quizLocale,
              title: response.title,
              description: response.description,
              is_sample: response.source === "mock",
              quiz_id: response.quiz_id,
              question_type: questionType,
              num_questions: numQuestions,
              difficulty_level: difficultyLevel,
              profession: response.title,
              audience_type: resolvedAudienceType,
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
          audienceType: resolvedAudienceType,
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
        audience_type: resolvedAudienceType,
        difficulty_level: difficultyLevel,
        token: aiProvider === "huggingface" ? token : undefined,
        ai_provider: aiProvider,
        live_quiz_enabled: enableLiveQuiz,
        time_limit_minutes: enableLiveQuiz ? liveDurationMinutes : undefined,
        access_code_expires_at: enableLiveQuiz
          ? new Date(liveAccessExpiresAt).toISOString()
          : undefined,
        participant_access_mode: enableLiveQuiz
          ? participantAccessMode
          : undefined,
        invited_emails: enableLiveQuiz ? invitedEmails : undefined,
        send_email_invitations: enableLiveQuiz
          ? sendEmailInvitations
          : undefined,
        content_locale: quizLocale,
        allow_fallback: allowSampleFallback && sampleAvailable,
      };

      const client =
        enableLiveQuiz || TokenService.hasTokens() ? api : publicApi;
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
              content_locale: data?.content_locale || quizLocale,
              title: data?.title || profession,
              description: data?.description,
              is_sample: data?.source === "mock",
              question_type: questionType,
              num_questions: numQuestions,
              difficulty_level: difficultyLevel,
              profession: data?.title || profession,
              audience_type: resolvedAudienceType,
              custom_instruction: customInstruction,
            },
            questions,
          );
          canonicalQuizId =
            canonicalQuizId || historyResponse?.data?.quiz_id || "";
        } catch (historyError) {
          console.error("Error saving quiz history:", historyError);
        }
      }

      const generatedQuizView = {
        id: canonicalQuizId || undefined,
        quiz_id: canonicalQuizId || undefined,
        title: data?.title || profession || `${questionType} Quiz`,
        content_locale: data?.content_locale || quizLocale,
        source: data?.source,
        description:
          data?.description ||
          customInstruction ||
          `A ${difficultyLevel} ${questionType} quiz for ${resolvedAudienceType}.`,
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
        audienceType: resolvedAudienceType,
        difficultyLevel,
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
    } catch (error: unknown) {
      const typedError = error as ApiErrorLike;
      const detail = typedError?.response?.data?.detail;
      const providerErrorKeys: Record<string, string> = {
        notConfigured: "quizProvider.notConfigured",
        credentials: "quizProvider.credentials",
        billing: "quizProvider.billing",
        quota: "quizProvider.quota",
        model: "quizProvider.model",
        invalidOutput: "quizProvider.invalidOutput",
        blocked: "quizProvider.blocked",
        timeout: "quizProvider.timeout",
        unavailable: "quizProvider.unavailable",
      };
      setErrorMessage(
        (typeof detail === "string"
          ? detail
          : detail?.code && providerErrorKeys[detail.code]
            ? uiText(providerErrorKeys[detail.code], {
                provider: detail.provider || aiProvider,
              })
            : detail?.message) ||
          typedError?.message ||
          uiText("m0aacbdeb5c3065b8"),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto bg-[#f7f8fa] rounded-xl p-10 shadow-lg">
      {persona ? (
        <PersonaBadge
          userType={persona.userType}
          className="mb-6"
          audienceFallback={t("learner", "plural")}
          appliedDefaults={{
            audienceType,
            difficultyLevel,
            numQuestions,
            questionType,
          }}
        />
      ) : null}
      <form onSubmit={(e) => e.preventDefault()}>
        <QuizGenerationSection
          generationMode={generationMode}
          setGenerationMode={setGenerationMode}
          profession={profession}
          setProfession={setProfession}
          professionPlaceholder={personaTopicPlaceholder}
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
          setAudienceType={markGenerationFieldTouched(
            "audienceType",
            setAudienceType,
          )}
          customInstruction={customInstruction}
          setCustomInstruction={markGenerationFieldTouched(
            "customInstruction",
            setCustomInstruction,
          )}
          numQuestions={numQuestions}
          setNumQuestions={markGenerationFieldTouched(
            "numQuestions",
            setNumQuestions,
          )}
          questionType={questionType}
          setQuestionType={markGenerationFieldTouched(
            "questionType",
            setQuestionType,
          )}
          difficultyLevel={difficultyLevel}
          setDifficultyLevel={markGenerationFieldTouched(
            "difficultyLevel",
            setDifficultyLevel,
          )}
          token={token}
          showTokenInput={aiProvider === "huggingface"}
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
                {uiText("m6936063ced1ea266")}
              </span>
              <span className="mt-1 block text-xs text-gray-500">
                {uiText("mbaacd1e96806262c")}
              </span>
            </span>
          </label>

          {enableLiveQuiz && (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-semibold text-[#2C3E50]">
                {uiText("m5232eb04a336ab88")}
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
                {uiText("m4090711b316909a5")}
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
                {uiText("m6ab7c606d3128746")}
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
                  <option value="public">{uiText("m178b790b1cb2c176")}</option>
                  <option value="restricted">
                    {uiText("m0c906cdd09708c8b")}
                  </option>
                  <option value="invited_only">
                    {uiText("mf9636e9a7397b7af")}
                  </option>
                </select>
              </label>
              <label className="block text-sm font-semibold text-[#2C3E50] md:col-span-2">
                {uiText("m26f1e46c9dfb0e3f")}
                <textarea
                  value={invitedEmailsText}
                  onChange={(event) => setInvitedEmailsText(event.target.value)}
                  placeholder={uiText("mefe42627ddbff54d")}
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
                {uiText("ma04fe96c22a26440")}
              </label>
            </div>
          )}
        </section>

        <section className="mt-6 rounded-md border border-slate-200 bg-white p-5">
          <label className="mb-2 block font-medium" htmlFor="quiz-ai-provider">
            {uiText("quizProvider.title")}
          </label>
          <select
            id="quiz-ai-provider"
            value={aiProvider}
            disabled={loading}
            onChange={(event) =>
              setAiProvider(event.target.value as "huggingface" | "gemini")
            }
            className="mb-2 w-full rounded border border-gray-300 bg-white p-2 text-gray-900"
          >
            <option value="huggingface">
              {uiText("quizProvider.huggingface")}
            </option>
            <option value="gemini">{uiText("quizProvider.gemini")}</option>
          </select>
          <p className="text-sm text-gray-600">
            {uiText(
              aiProvider === "gemini"
                ? "quizProvider.geminiHelp"
                : "quizProvider.huggingfaceHelp",
            )}
          </p>
        </section>

        <section className="my-6 rounded-md border border-slate-200 bg-white p-5">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={allowSampleFallback && sampleAvailable}
              disabled={loading || !sampleAvailable}
              onChange={(event) => setAllowSampleFallback(event.target.checked)}
            />
            <span>{uiText("quizLanguage.allowSample")}</span>
          </label>
          <p className="mt-2 text-xs text-gray-600">
            {uiText("quizLanguage.sampleLimit")}
          </p>
          <button
            type="button"
            aria-expanded={languageExpanded}
            aria-controls={languageOptionsId}
            disabled={loading}
            onClick={() => setLanguageExpanded((expanded) => !expanded)}
            className="mt-4 flex w-full items-center justify-between gap-3 rounded border border-slate-300 p-3 text-left font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
          >
            <span>
              {uiText("quizLanguage.title")}:{" "}
              {LOCALE_DISPLAY_NAMES[quizLocale] || quizLocale} ({quizLocale})
            </span>
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              className={`h-5 w-5 shrink-0 transition-transform ${languageExpanded ? "rotate-180" : ""}`}
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
          </button>
          <p className="mt-2 text-sm text-gray-600">
            {uiText("quizLanguage.help")}
          </p>
          <div
            id={languageOptionsId}
            hidden={!languageExpanded}
            className="mt-4"
          >
            <LanguagePicker
              value={quizLocale}
              onChange={setQuizLocaleOverride}
              disabled={loading}
              label={uiText("quizLanguage.title")}
            />
          </div>
        </section>

        {errorMessage && (
          <p className="text-red-500 mb-4 font-medium">{errorMessage}</p>
        )}

        <GenerateButton onClick={handleGenerateQuiz} loading={loading} />
      </form>
    </div>
  );
}
