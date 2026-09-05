import type { CreateTrainingRunPayload } from "@features/training/api/trainingRunApi";

type PendingKeys = Map<string, string>;

export const trainingRunIntentFingerprint = (
  payload: CreateTrainingRunPayload,
): string => {
  const recipientEmails = Array.from(
    new Set(payload.recipient_emails.map((email) => email.trim().toLowerCase())),
  ).sort();

  // This mirrors the server's request-fingerprint normalization. Keeping the
  // same intent stable across whitespace or recipient-order changes avoids
  // needlessly creating another run after a lost response.
  return JSON.stringify({
    quiz_id: payload.quiz_id,
    kind: payload.kind,
    purpose: payload.purpose,
    title: (payload.title ?? "").trim(),
    time_limit_minutes: payload.time_limit_minutes,
    closes_at: payload.closes_at,
    due_at: payload.due_at ?? null,
    access_mode: payload.access_mode,
    recipient_emails: recipientEmails,
    max_attempts: payload.max_attempts,
    send_email_invitations: payload.send_email_invitations,
  });
};

export const idempotencyKeyForTrainingRun = (
  pendingKeys: PendingKeys,
  payload: CreateTrainingRunPayload,
  createKey: () => string,
): string => {
  const fingerprint = trainingRunIntentFingerprint(payload);
  const existing = pendingKeys.get(fingerprint);
  if (existing) return existing;

  const key = createKey();
  pendingKeys.set(fingerprint, key);
  return key;
};

export const clearTrainingRunIdempotencyKey = (
  pendingKeys: PendingKeys,
  payload: CreateTrainingRunPayload,
): void => {
  pendingKeys.delete(trainingRunIntentFingerprint(payload));
};
