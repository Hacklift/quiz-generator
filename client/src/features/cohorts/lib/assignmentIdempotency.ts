import type { AssignmentInput } from "../api/cohortDeliveryApi";

export function assignmentFingerprint(input: AssignmentInput): string {
  return JSON.stringify({
    quiz_id: input.quiz_id,
    title: input.title.trim(),
    cohort_id: input.cohort_id ?? null,
    recipient_user_ids: Array.from(new Set(input.recipient_user_ids ?? [])).sort(),
    available_from: input.available_from ?? null,
    due_at: input.due_at ?? null,
    closes_at: input.closes_at,
    max_attempts: input.max_attempts,
    time_limit_minutes: input.time_limit_minutes,
    passing_threshold_percentage: input.passing_threshold_percentage,
    send_email_invitations: input.send_email_invitations,
  });
}

export function assignmentCreationKey(keys: Map<string, string>, input: AssignmentInput): string {
  const fingerprint = assignmentFingerprint(input);
  let key = keys.get(fingerprint);
  if (!key) {
    key = crypto.randomUUID();
    keys.set(fingerprint, key);
  }
  return key;
}

export function completeAssignmentCreation(keys: Map<string, string>, input: AssignmentInput): void {
  keys.delete(assignmentFingerprint(input));
}
