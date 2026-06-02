import publicApi from "@shared/api/publicHttp";
import { api } from "@shared/api/http";
import { TokenService } from "@shared/auth/tokenService";

const tokenStorageKey = (sessionId: string) => `live_quiz_token_${sessionId}`;

export interface LiveQuizPreview {
  quiz_id: string;
  title: string;
  total_questions: number;
  time_limit_minutes: number;
  access_code_expires_at: string;
  participant_access_mode: string;
}

export interface StartLiveQuizResponse {
  session_id: string;
  participant_token: string;
  started_at: string;
  expires_at: string;
  server_now: string;
  time_limit_minutes: number;
  duration_seconds: number;
  remaining_seconds: number;
  redirect_url: string;
}

export interface LiveQuizQuestion {
  question_index: number;
  question: string;
  options?: string[];
  question_type?: string;
  selected_answer?: string | null;
}

export interface LiveQuizSessionState {
  session_id: string;
  quiz_id: string;
  title: string;
  participant_name: string;
  participant_email?: string | null;
  started_at: string;
  expires_at: string;
  server_now: string;
  submitted_at?: string | null;
  status: "active" | "joined" | "disconnected" | "submitted" | "expired";
  current_question_index: number;
  total_questions: number;
  time_limit_minutes: number;
  duration_seconds: number;
  remaining_seconds: number;
  question?: LiveQuizQuestion | null;
  answers: Array<{
    question_index: number;
    selected_answer: string;
    answered_at: string;
  }>;
  score?: number | null;
  percentage?: number | null;
  auto_submitted: boolean;
}

export interface LiveQuizResult {
  status: "submitted" | "already_submitted";
  score: number;
  total_questions: number;
  percentage: number;
  submitted_at: string;
  auto_submitted: boolean;
}

export interface ParticipantRow {
  session_id: string;
  participant_name: string;
  participant_email?: string | null;
  score?: number | null;
  total_questions: number;
  percentage?: number | null;
  joined_at?: string | null;
  started_at?: string | null;
  submitted_at?: string | null;
  duration_seconds?: number | null;
  progress?: number | null;
  current_question_number?: number | null;
  progress_percentage?: number | null;
  status: string;
  auto_submitted: boolean;
}

export interface AccessCodeResponse {
  quiz_id: string;
  access_code: string;
  live_quiz_enabled: boolean;
  time_limit_minutes: number;
  access_code_expires_at: string;
  participant_access_mode: string;
  invited_emails: string[];
  invitations_created: number;
  invitations_delivered: number;
}

export interface LiveQuizSummary {
  quiz_id: string;
  title: string;
  access_code?: string | null;
  status: string;
  created_at?: string | null;
  participant_count: number;
  completed_count: number;
  average_score?: number | null;
}

export type LiveQuizParticipantsEvent =
  | {
      type: "participants_snapshot";
      quiz_id: string;
      participants: ParticipantRow[];
    }
  | {
      type:
        | "participant_joined"
        | "participant_progress"
        | "participant_submitted"
        | "participant_disconnected";
      quiz_id: string;
      participant: ParticipantRow;
    };

const authHeaders = (sessionId: string) => {
  const token = getParticipantToken(sessionId);
  if (!token) {
    throw new Error("Participant token missing for this live quiz session.");
  }
  return { "X-Participant-Token": token };
};

export const saveParticipantToken = (sessionId: string, token: string) => {
  if (typeof window !== "undefined") {
    localStorage.setItem(tokenStorageKey(sessionId), token);
  }
};

export const getParticipantToken = (sessionId: string): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(tokenStorageKey(sessionId));
};

export const liveQuizService = {
  async createAccessCode(payload: {
    quizId: string;
    time_limit_minutes: number;
    access_code_expires_at: string;
    participant_access_mode?: "public" | "restricted" | "invited_only";
    invited_emails?: string[];
    send_email_invitations?: boolean;
  }): Promise<AccessCodeResponse> {
    const { quizId, ...body } = payload;
    const { data } = await api.post(
      `/api/v1/quizzes/${quizId}/access-code`,
      body,
    );
    return data;
  },

  async validateAccessCode(code: string): Promise<LiveQuizPreview> {
    const { data } = await publicApi.get(
      `/api/v1/quizzes/access/${encodeURIComponent(code.trim().toUpperCase())}`,
    );
    return data;
  },

  async startSession(payload: {
    code: string;
    participant_name: string;
    participant_email?: string;
  }): Promise<StartLiveQuizResponse> {
    const { code, ...body } = payload;
    const { data } = await publicApi.post(
      `/api/v1/quizzes/access/${encodeURIComponent(code.trim().toUpperCase())}/start`,
      body,
    );
    saveParticipantToken(data.session_id, data.participant_token);
    return data;
  },

  async getSession(sessionId: string): Promise<LiveQuizSessionState> {
    const { data } = await publicApi.get(
      `/api/v1/live-quiz-sessions/${sessionId}`,
      { headers: authHeaders(sessionId) },
    );
    return data;
  },

  async saveAnswer(
    sessionId: string,
    questionIndex: number,
    selectedAnswer: string,
    nextQuestionIndex?: number,
  ) {
    const { data } = await publicApi.post(
      `/api/v1/live-quiz-sessions/${sessionId}/answers`,
      {
        question_index: questionIndex,
        selected_answer: selectedAnswer,
        next_question_index: nextQuestionIndex,
      },
      { headers: authHeaders(sessionId) },
    );
    return data;
  },

  async submitSession(
    sessionId: string,
    autoSubmitted = false,
  ): Promise<LiveQuizResult> {
    const { data } = await publicApi.post(
      `/api/v1/live-quiz-sessions/${sessionId}/submit`,
      null,
      {
        headers: authHeaders(sessionId),
        params: { auto_submitted: autoSubmitted },
      },
    );
    return data;
  },

  async markDisconnected(sessionId: string): Promise<void> {
    await publicApi.post(
      `/api/v1/live-quiz-sessions/${sessionId}/disconnect`,
      null,
      { headers: authHeaders(sessionId) },
    );
  },

  async listParticipants(quizId: string): Promise<ParticipantRow[]> {
    const { data } = await api.get(
      `/api/v1/quizzes/${quizId}/live-sessions/participants`,
    );
    return data;
  },

  async listLiveQuizzes(): Promise<LiveQuizSummary[]> {
    const { data } = await api.get("/api/v1/quizzes/live");
    return data;
  },

  subscribeParticipants(
    quizId: string,
    onEvent: (event: LiveQuizParticipantsEvent) => void,
    onClose?: () => void,
  ): WebSocket | null {
    if (typeof window === "undefined") return null;
    const token = TokenService.getAccessToken();
    if (!token) return null;

    const baseUrl =
      api.defaults.baseURL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "http://localhost:8000";
    const wsBaseUrl = baseUrl.replace(/^http/i, "ws").replace(/\/$/, "");
    const socket = new WebSocket(
      `${wsBaseUrl}/api/v1/quizzes/${encodeURIComponent(
        quizId,
      )}/live-sessions/ws?token=${encodeURIComponent(token)}`,
    );

    socket.onmessage = (message) => {
      try {
        onEvent(JSON.parse(message.data));
      } catch {
        // Ignore malformed websocket payloads; polling fallback stays active.
      }
    };
    socket.onclose = () => {
      onClose?.();
    };
    return socket;
  },
};
