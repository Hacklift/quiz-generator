import { api } from "@shared/api/http";
import type { ParentPracticeGenerationParams } from "@features/parent-practice/config/presets";

export interface ParentPracticeReady {
  quizId: string;
  title: string;
  questionCount: number;
  accessCode: string;
  durationMinutes: number;
}

export async function createParentPractice(
  params: ParentPracticeGenerationParams,
  durationMinutes = 20,
): Promise<ParentPracticeReady> {
  if (
    !Number.isInteger(durationMinutes) ||
    durationMinutes < 1 ||
    durationMinutes > 180
  ) {
    throw new Error("Duration must be a whole number between 1 and 180 minutes.");
  }
  const allowFallback =
    process.env.NEXT_PUBLIC_PARENT_PRACTICE_ALLOW_FALLBACK === "true";
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  const { data } = await api.post("/api/get-questions", {
    ...params,
    live_quiz_enabled: true,
    time_limit_minutes: durationMinutes,
    access_code_expires_at: expiresAt.toISOString(),
    participant_access_mode: "public",
    invited_emails: [],
    send_email_invitations: false,
    allow_fallback: allowFallback,
  });

  // The generic generator can fall back to unrelated static questions. A
  // Parent preset must never claim that unrelated content is valid practice.
  if (data?.ai_down && !allowFallback) {
    throw new Error(
      "Practice generation is temporarily unavailable. Please try again.",
    );
  }
  if (!data?.quiz_id || !data?.access_code || !Array.isArray(data?.questions)) {
    throw new Error("Practice could not be prepared. Please try again.");
  }

  return {
    quizId: data.quiz_id,
    title: params.profession,
    questionCount: data.questions.length,
    accessCode: data.access_code,
    durationMinutes,
  };
}
