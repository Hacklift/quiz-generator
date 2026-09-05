import { api } from "@shared/api/http";

export type TrainingKind = "business" | "compliance";
export type TrainingPurpose =
  | "onboarding"
  | "product_knowledge"
  | "harassment_prevention"
  | "health_and_safety"
  | "custom";
export type TrainingAccessMode = "public" | "assigned_only";

export interface TrainingRunSummary {
  id: string;
  quiz_id: string;
  title: string;
  kind: TrainingKind;
  purpose: TrainingPurpose;
  status: "open" | "closed";
  access_mode: TrainingAccessMode;
  access_code?: string | null;
  access_url?: string | null;
  time_limit_minutes: number;
  due_at?: string | null;
  closes_at: string;
  closed_at?: string | null;
  created_at: string;
  assigned_count: number;
  started_count: number;
  completed_count: number;
  average_score?: number | null;
}

export interface TrainingCompletionRow {
  assignment_id: string;
  recipient_email?: string | null;
  recipient_name?: string | null;
  status: "assigned" | "in_progress" | "incomplete" | "completed";
  due_at?: string | null;
  attempts_used: number;
  max_attempts?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  latest_score?: number | null;
  latest_percentage?: number | null;
}

export interface TrainingRunDetail extends TrainingRunSummary {
  completion_register: TrainingCompletionRow[];
}

export interface TrainingAssignment {
  id: string;
  training_run_id: string;
  quiz_id: string;
  title: string;
  kind: TrainingKind;
  purpose: TrainingPurpose;
  status: "assigned" | "in_progress" | "incomplete" | "completed";
  due_at?: string | null;
  closes_at: string;
  latest_start_at: string;
  is_overdue: boolean;
  max_attempts?: number | null;
  attempts_used: number;
  can_retry: boolean;
  latest_score?: number | null;
  latest_percentage?: number | null;
  completed_at?: string | null;
}

export interface OwnedQuiz {
  id: string;
  title: string;
  quiz_type: string;
  created_at?: string | null;
}

export interface TrainingAccessPreview {
  title: string;
  total_questions: number;
  time_limit_minutes: number;
  closes_at: string;
}

export interface StartedTrainingSession {
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

export const trainingRunApi = {
  async listOwnedQuizzes(): Promise<OwnedQuiz[]> {
    const { data } = await api.get("/api/v1/training-runs/owned-quizzes");
    return data;
  },

  async createRun(payload: {
    quiz_id: string;
    kind: TrainingKind;
    purpose: TrainingPurpose;
    title?: string;
    time_limit_minutes: number;
    closes_at: string;
    due_at?: string;
    access_mode: TrainingAccessMode;
    recipient_emails: string[];
    max_attempts: number | null;
    send_email_invitations: boolean;
  }, idempotencyKey: string): Promise<TrainingRunSummary> {
    const { data } = await api.post("/api/v1/training-runs", payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  async listRuns(): Promise<TrainingRunSummary[]> {
    const { data } = await api.get("/api/v1/training-runs");
    return data;
  },

  async getRun(runId: string): Promise<TrainingRunDetail> {
    const { data } = await api.get(`/api/v1/training-runs/${runId}`);
    return data;
  },

  async closeRun(runId: string): Promise<TrainingRunSummary> {
    const { data } = await api.post(`/api/v1/training-runs/${runId}/close`, {
      confirm: true,
    });
    return data;
  },

  async listMyAssignments(): Promise<TrainingAssignment[]> {
    const { data } = await api.get("/api/v1/training-assignments/mine");
    return data;
  },

  async startAssignment(assignmentId: string): Promise<StartedTrainingSession> {
    const { data } = await api.post(
      `/api/v1/training-assignments/${assignmentId}/start`,
    );
    return data;
  },
};
