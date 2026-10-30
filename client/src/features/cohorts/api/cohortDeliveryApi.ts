import { api } from "@shared/api/http";
import type { StartedTrainingSession } from "@features/training/api/trainingRunApi";
import type { GradedAnswer } from "@features/live-quiz/api/liveQuizService";

export interface Page<T> { items: T[]; next_cursor: string | null }
export type CohortKind = "class" | "course" | "team" | "department" | "campaign";
export interface Cohort {
  id: string;
  organization_id: string;
  kind: CohortKind;
  name: string;
  parent_cohort_id: string | null;
  status: "active" | "archived";
  can_manage?: boolean;
  can_assign?: boolean;
  can_report?: boolean;
}
export interface CohortInput { name: string; kind: CohortKind; parent_cohort_id: string | null }
export interface MemberOption { user_id: string; name: string }
export interface CohortMember extends MemberOption {
  role: "facilitator" | "member" | "guardian";
  can_assign: boolean;
  can_report: boolean;
}
export interface MemberInput {
  user_id: string;
  role: CohortMember["role"];
  can_assign: boolean;
  can_report: boolean;
}
export interface AssignmentInput {
  quiz_id: string;
  cohort_id?: string;
  recipient_user_ids?: string[];
  title: string;
  available_from?: string;
  due_at?: string;
  closes_at: string;
  max_attempts: 1 | 2 | null;
  time_limit_minutes: number;
  passing_threshold_percentage: number;
  send_email_invitations: boolean;
}
export interface Assignment {
  id: string;
  title: string;
  quiz_id: string;
  quiz_revision_id: string;
  cohort_id: string | null;
  status: string;
  available_from?: string | null;
  due_at?: string | null;
  closes_at: string;
  time_limit_minutes: number;
  max_attempts: number | null;
  passing_threshold_percentage: number;
  can_manage?: boolean;
  can_report?: boolean;
  can_start?: boolean;
  can_resume?: boolean;
  recipient_status?: string;
  active_session_id?: string | null;
  has_completed?: boolean;
  attempts_used?: number;
  latest_percentage?: number | null;
  participant_count?: number;
  completed_count?: number;
  outstanding_count?: number;
  completion_percentage?: number;
  average_percentage?: number | null;
  summary_availability?: "available" | "unavailable";
  recipients?: AssignmentRecipient[];
  next_cursor?: string | null;
  my_assignment?: AssignmentRecipient;
}
export interface AssignmentRecipient {
  recipient_id: string;
  user_id: string | null;
  recipient_name: string | null;
  recipient_status: string;
  has_completed: boolean;
  can_start: boolean;
  can_resume?: boolean;
  available: boolean;
  active_session_id?: string | null;
  attempts_used: number;
  max_attempts: number | null;
  latest_score?: number | null;
  latest_percentage?: number | null;
  completed_at?: string | null;
}
export interface CohortProgress {
  id: string;
  title: string;
  participant_count: number;
  completed_count: number;
  outstanding_count: number;
  completion_percentage: number;
  average_percentage: number | null;
  summary_availability?: "available" | "unavailable";
}
export interface AssignableQuiz { id: string; title: string }
export interface AssignedAttempt {
  id: string;
  status: string;
  score?: number | null;
  percentage?: number | null;
  started_at?: string | null;
  submitted_at?: string | null;
  completed_at?: string | null;
}
export interface AssignedAttemptDetail extends AssignedAttempt {
  questions?: { question: string; options?: string[] }[];
  graded_answers: GradedAnswer[];
}
const id = encodeURIComponent;
const scopeHeaders = (organizationId: string) => ({ "X-Organization-ID": organizationId });
const params = (cursor?: string) => ({ params: cursor ? { cursor } : undefined });
async function get<T>(url: string, cursor?: string): Promise<T> {
  return (await api.get<T>(url, params(cursor))).data;
}
export const cohortDeliveryApi = {
  async listCohorts(cursor?: string, status: "active" | "archived" = "active"): Promise<Page<Cohort>> {
    return (await api.get<Page<Cohort>>("/api/cohorts", { params: { ...(cursor ? { cursor } : {}), status } })).data;
  },
  getCohort: (cohortId: string) => get<Cohort>(`/api/cohorts/${id(cohortId)}`),
  async createCohort(input: CohortInput, organizationId: string): Promise<Cohort> {
    return (await api.post<Cohort>("/api/cohorts", input, { headers: scopeHeaders(organizationId) })).data;
  },
  async updateCohort(cohortId: string, input: CohortInput, organizationId: string): Promise<Cohort> {
    return (await api.patch<Cohort>(`/api/cohorts/${id(cohortId)}`, input, { headers: scopeHeaders(organizationId) })).data;
  },
  async archiveCohort(cohortId: string, organizationId: string): Promise<void> {
    await api.delete(`/api/cohorts/${id(cohortId)}`, { headers: scopeHeaders(organizationId) });
  },
  listMembers: (cohortId: string, cursor?: string) => get<Page<CohortMember>>(`/api/cohorts/${id(cohortId)}/members`, cursor),
  memberOptions: (cursor?: string) => get<Page<MemberOption>>("/api/cohorts/member-options", cursor),
  recipientOptions: (cursor?: string) => get<Page<MemberOption>>("/api/v1/assignments/recipient-options", cursor),
  async setMember(cohortId: string, input: MemberInput, organizationId: string): Promise<CohortMember> {
    return (await api.post<CohortMember>(`/api/cohorts/${id(cohortId)}/members`, input, { headers: scopeHeaders(organizationId) })).data;
  },
  async removeMember(cohortId: string, userId: string, organizationId: string): Promise<void> {
    await api.delete(`/api/cohorts/${id(cohortId)}/members/${id(userId)}`, { headers: scopeHeaders(organizationId) });
  },
  progress: (cohortId: string, cursor?: string) => get<Page<CohortProgress>>(`/api/cohorts/${id(cohortId)}/progress`, cursor),
  listAssignments: (cursor?: string) => get<Page<Assignment>>("/api/v1/assignments", cursor),
  myAssignments: (cursor?: string) => get<Page<Assignment>>("/api/v1/assignments/mine", cursor),
  quizzes: (cursor?: string) => get<Page<AssignableQuiz>>("/api/v1/assignments/quizzes", cursor),
  getAssignment: (assignmentId: string, cursor?: string) => get<Assignment>(`/api/v1/assignments/${id(assignmentId)}`, cursor),
  async createAssignment(input: AssignmentInput, key: string, organizationId: string): Promise<Assignment> {
    return (await api.post<Assignment>("/api/v1/assignments", input, { headers: { ...scopeHeaders(organizationId), "Idempotency-Key": key } })).data;
  },
  async startAssignment(assignmentId: string, organizationId: string): Promise<StartedTrainingSession> {
    return (await api.post<StartedTrainingSession>(`/api/v1/assignments/${id(assignmentId)}/start`, undefined, { headers: scopeHeaders(organizationId) })).data;
  },
  async closeAssignment(assignmentId: string, organizationId: string): Promise<Assignment> {
    return (await api.post<Assignment>(`/api/v1/assignments/${id(assignmentId)}/close`, { confirm: true }, { headers: scopeHeaders(organizationId) })).data;
  },
  attempts: (assignmentId: string, userId: string, cursor?: string) => get<Page<AssignedAttempt>>(
    `/api/v1/assignments/${id(assignmentId)}/recipients/${id(userId)}/attempts`, cursor,
  ),
  attempt: (assignmentId: string, userId: string, sessionId: string) => get<AssignedAttemptDetail>(
    `/api/v1/assignments/${id(assignmentId)}/recipients/${id(userId)}/attempts/${id(sessionId)}`,
  ),
};
